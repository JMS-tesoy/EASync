"""
Toxic Flow Detection Algorithm
================================

This module implements the Trust Score calculation system that identifies
and auto-pauses users exhibiting toxic flow patterns.

Philosophy:
-----------
- Trust Score ranges from 0-100 (100 = perfect, 0 = toxic)
- Calculated based on rolling window of protection events
- Auto-pause triggers when score drops below threshold
- Includes recovery mechanism for rehabilitated users

Scoring Rules:
--------------
- TTL Expiry: -5 points (indicates slow VPS or network issues)
- Sequence Gap: -20 points (indicates missing signals or malicious replay)
- Price Deviation: -3 points (market volatility, less severe)
- Replay Attack: -50 points (critical security violation)
- Successful execution: +1 point (capped at 100)

Auto-Pause Threshold: 50
Recovery: Score increases by +10 every 24 hours without incidents
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ProtectionEventReason(Enum):
    """Matches the PostgreSQL enum"""
    REPLAY_ATTACK = "REPLAY_ATTACK"
    DUPLICATE_SEQ = "DUPLICATE_SEQ"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    TTL_EXPIRED = "TTL_EXPIRED"
    PRICE_DEVIATION = "PRICE_DEVIATION"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    STATE_LOCKED = "STATE_LOCKED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


@dataclass
class ProtectionEvent:
    """Represents a single protection event from the database"""
    event_id: str
    event_time: datetime
    user_id: str
    subscription_id: str
    reason: ProtectionEventReason
    latency_ms: int
    signal_sequence: int


@dataclass
class TrustScoreResult:
    """Result of trust score calculation"""
    user_id: str
    current_score: int
    previous_score: int
    score_delta: int
    should_pause: bool
    total_events_analyzed: int
    event_breakdown: Dict[str, int]
    recommendation: str


# Scoring weights for each protection event type
SCORE_PENALTIES = {
    ProtectionEventReason.REPLAY_ATTACK: -50,      # Critical security violation
    ProtectionEventReason.DUPLICATE_SEQ: -30,      # Likely malicious
    ProtectionEventReason.SEQUENCE_GAP: -20,       # Missing signals or replay attempt
    ProtectionEventReason.TTL_EXPIRED: -5,         # Slow VPS or network jitter
    ProtectionEventReason.PRICE_DEVIATION: -3,     # Market volatility (less severe)
    ProtectionEventReason.INSUFFICIENT_FUNDS: -10, # Financial issue
    ProtectionEventReason.STATE_LOCKED: -5,        # Consequence of previous issues
    ProtectionEventReason.INVALID_SIGNATURE: -40,  # Security violation
    ProtectionEventReason.RATE_LIMIT_EXCEEDED: -15 # Potential abuse
}

# Configuration
AUTO_PAUSE_THRESHOLD = 50
RECOVERY_POINTS_PER_DAY = 10
ROLLING_WINDOW_HOURS = 24
MAX_SCORE = 100
MIN_SCORE = 0


class ToxicFlowDetector:
    """
    Analyzes protection logs to calculate user trust scores and trigger auto-pause.
    
    This class is designed to be called by a background worker that consumes
    protection_logs from the database or a message queue.
    """
    
    def __init__(self, db_connection):
        """
        Initialize the detector with a database connection.
        
        Args:
            db_connection: Database connection object (e.g., asyncpg pool)
        """
        self.db = db_connection
    
    async def calculate_trust_score(
        self,
        user_id: str,
        window_hours: int = ROLLING_WINDOW_HOURS
    ) -> TrustScoreResult:
        """
        Calculate trust score for a user based on recent protection events.
        
        This is the MAIN ENTRY POINT for trust score calculation.
        
        CRITICAL FIX: Uses database transaction with SELECT FOR UPDATE
        to prevent race conditions when multiple workers process same user.
        
        Args:
            user_id: UUID of the user to analyze
            window_hours: Rolling window size in hours (default: 24)
        
        Returns:
            TrustScoreResult with score, breakdown, and recommendation
        """
        logger.info(f"Calculating trust score for user {user_id}")
        
        # CRITICAL FIX: Wrap entire calculation in transaction with row lock
        async with self.db.transaction():
            # Lock the user row to prevent concurrent modifications
            query_lock = """
                SELECT trust_score 
                FROM users 
                WHERE user_id = $1
                FOR UPDATE  -- CRITICAL: Row-level lock
            """
            row = await self.db.fetchrow(query_lock, user_id)
            current_score = row['trust_score'] if row else 100
            
            # Fetch protection events from rolling window
            events = await self._fetch_protection_events(user_id, window_hours)
            
            # Calculate score delta based on events
            score_delta = 0
            event_breakdown = {}
            
            for event in events:
                penalty = SCORE_PENALTIES.get(event.reason, 0)
                score_delta += penalty
                
                # Track event counts by type
                reason_str = event.reason.value
                event_breakdown[reason_str] = event_breakdown.get(reason_str, 0) + 1
            
            # Apply recovery bonus if no recent incidents
            if len(events) == 0:
                recovery_bonus = await self._calculate_recovery_bonus(user_id)
                score_delta += recovery_bonus
            
            # Calculate new score (clamped to [MIN_SCORE, MAX_SCORE])
            new_score = max(MIN_SCORE, min(MAX_SCORE, current_score + score_delta))
            
            # Determine if user should be paused
            should_pause = new_score < AUTO_PAUSE_THRESHOLD
            
            # Generate recommendation
            recommendation = self._generate_recommendation(
                new_score, event_breakdown, should_pause
            )
            
            result = TrustScoreResult(
                user_id=user_id,
                current_score=new_score,
                previous_score=current_score,
                score_delta=score_delta,
                should_pause=should_pause,
                total_events_analyzed=len(events),
                event_breakdown=event_breakdown,
                recommendation=recommendation
            )
            
            # Update database with new score (within same transaction)
            await self.db.execute(
                """
                UPDATE users 
                SET trust_score = $2, updated_at = NOW() 
                WHERE user_id = $1
                """,
                user_id, new_score
            )
            
            # Transaction commits here, releasing lock
        
        # Trigger auto-pause if necessary (outside transaction)
        if should_pause and current_score >= AUTO_PAUSE_THRESHOLD:
            # Score just dropped below threshold
            await self._trigger_auto_pause(user_id, result)
        
        logger.info(
            f"Trust score for {user_id}: {current_score} -> {new_score} "
            f"(delta: {score_delta:+d}, events: {len(events)})"
        )
        
        return result
    
    async def _fetch_protection_events(
        self,
        user_id: str,
        window_hours: int
    ) -> List[ProtectionEvent]:
        """
        Fetch protection events from the database within the rolling window.
        
        SQL Query:
        ----------
        SELECT event_id, event_time, user_id, subscription_id, reason, 
               latency_ms, signal_sequence
        FROM protection_logs
        WHERE user_id = $1
          AND event_time > NOW() - INTERVAL '$2 hours'
        ORDER BY event_time DESC;
        """
        query = """
            SELECT event_id, event_time, user_id, subscription_id, reason,
                   latency_ms, signal_sequence
            FROM protection_logs
            WHERE user_id = $1
              AND event_time > NOW() - INTERVAL '1 hour' * $2
            ORDER BY event_time DESC
        """
        
        rows = await self.db.fetch(query, user_id, window_hours)
        
        events = []
        for row in rows:
            events.append(ProtectionEvent(
                event_id=str(row['event_id']),
                event_time=row['event_time'],
                user_id=str(row['user_id']),
                subscription_id=str(row['subscription_id']),
                reason=ProtectionEventReason(row['reason']),
                latency_ms=row['latency_ms'],
                signal_sequence=row['signal_sequence']
            ))
        
        return events
    
    async def _get_current_score(self, user_id: str) -> int:
        """Get current trust score from users table"""
        query = "SELECT trust_score FROM users WHERE user_id = $1"
        row = await self.db.fetchrow(query, user_id)
        return row['trust_score'] if row else 100  # Default to perfect score
    
    async def _update_trust_score(self, user_id: str, new_score: int) -> None:
        """Update trust score in users table"""
        query = """
            UPDATE users
            SET trust_score = $2, updated_at = NOW()
            WHERE user_id = $1
        """
        await self.db.execute(query, user_id, new_score)
    
    async def _calculate_recovery_bonus(self, user_id: str) -> int:
        """
        Calculate recovery bonus for users with no recent incidents.
        
        Recovery: +10 points per 24 hours without protection events.
        """
        query = """
            SELECT MAX(event_time) as last_event
            FROM protection_logs
            WHERE user_id = $1
        """
        row = await self.db.fetchrow(query, user_id)
        
        if not row or not row['last_event']:
            return 0
        
        last_event_time = row['last_event']
        hours_since_last_event = (datetime.utcnow() - last_event_time).total_seconds() / 3600
        
        # Award recovery points for each full 24-hour period
        recovery_days = int(hours_since_last_event / 24)
        recovery_bonus = recovery_days * RECOVERY_POINTS_PER_DAY
        
        logger.debug(f"Recovery bonus for {user_id}: +{recovery_bonus} points")
        return recovery_bonus
    
    async def _trigger_auto_pause(
        self,
        user_id: str,
        score_result: TrustScoreResult
    ) -> None:
        """
        Trigger auto-pause for a user whose trust score dropped below threshold.
        
        Actions:
        --------
        1. Update all active subscriptions to STATE_PAUSED_TOXIC
        2. Log the pause event
        3. Send notification (email, webhook, etc.)
        """
        logger.warning(
            f"AUTO-PAUSE triggered for user {user_id}. "
            f"Trust score: {score_result.current_score}"
        )
        
        # Update all active subscriptions
        query = """
            UPDATE subscriptions
            SET state = 'PAUSED_TOXIC',
                paused_at = NOW(),
                paused_reason = $2,
                updated_at = NOW()
            WHERE subscriber_id = $1
              AND is_active = TRUE
              AND state != 'PAUSED_TOXIC'
        """
        
        pause_reason = (
            f"Auto-paused due to low trust score ({score_result.current_score}). "
            f"Events: {score_result.event_breakdown}"
        )
        
        await self.db.execute(query, user_id, pause_reason)
        
        # TODO: Send notification
        # await self.notification_service.send_auto_pause_alert(user_id, score_result)
        
        logger.info(f"User {user_id} subscriptions paused")
    
    def _generate_recommendation(
        self,
        score: int,
        event_breakdown: Dict[str, int],
        should_pause: bool
    ) -> str:
        """Generate human-readable recommendation based on score and events"""
        
        if should_pause:
            return (
                f"CRITICAL: Trust score {score} is below threshold ({AUTO_PAUSE_THRESHOLD}). "
                f"User has been auto-paused. Review event breakdown: {event_breakdown}"
            )
        
        if score < 70:
            return (
                f"WARNING: Trust score {score} is degraded. "
                f"Monitor for: {event_breakdown}. "
                f"Consider reaching out to user to diagnose VPS/network issues."
            )
        
        if score < 90:
            return (
                f"NOTICE: Trust score {score} is acceptable but not optimal. "
                f"Minor issues detected: {event_breakdown}"
            )
        
        return f"HEALTHY: Trust score {score}. No action required."


# ==============================================================================
# Background Worker Example
# ==============================================================================

async def trust_score_worker(db_pool):
    """
    Background worker that periodically recalculates trust scores.
    
    This should run as a separate process/container and consume protection_logs
    in real-time or on a schedule (e.g., every 5 minutes).
    
    Usage:
    ------
    asyncio.run(trust_score_worker(db_pool))
    """
    detector = ToxicFlowDetector(db_pool)
    
    while True:
        try:
            # Get all users with recent protection events
            query = """
                SELECT DISTINCT user_id
                FROM protection_logs
                WHERE event_time > NOW() - INTERVAL '1 hour'
            """
            
            async with db_pool.acquire() as conn:
                rows = await conn.fetch(query)
                
                for row in rows:
                    user_id = str(row['user_id'])
                    
                    try:
                        result = await detector.calculate_trust_score(user_id)
                        
                        if result.should_pause:
                            logger.critical(
                                f"User {user_id} auto-paused. Score: {result.current_score}"
                            )
                    except Exception as e:
                        logger.error(f"Failed to calculate trust score for {user_id}: {e}")
            
            # Sleep for 5 minutes before next run
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Trust score worker error: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute on error


# ==============================================================================
# CLI Tool for Manual Analysis
# ==============================================================================

async def analyze_user_cli(user_id: str, db_url: str):
    """
    CLI tool for manually analyzing a specific user's trust score.
    
    Usage:
    ------
    python toxic_flow.py --user-id <uuid> --db-url <postgres_url>
    """
    import asyncpg
    
    conn = await asyncpg.connect(db_url)
    detector = ToxicFlowDetector(conn)
    
    result = await detector.calculate_trust_score(user_id)
    
    print("\n" + "="*80)
    print(f"TRUST SCORE ANALYSIS: {user_id}")
    print("="*80)
    print(f"Current Score:  {result.current_score}")
    print(f"Previous Score: {result.previous_score}")
    print(f"Score Delta:    {result.score_delta:+d}")
    print(f"Should Pause:   {result.should_pause}")
    print(f"Events Analyzed: {result.total_events_analyzed}")
    print(f"\nEvent Breakdown:")
    for reason, count in result.event_breakdown.items():
        print(f"  - {reason}: {count}")
    print(f"\nRecommendation:\n{result.recommendation}")
    print("="*80 + "\n")
    
    await conn.close()


if __name__ == "__main__":
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Toxic Flow Detection CLI")
    parser.add_argument("--user-id", required=True, help="User UUID to analyze")
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    
    args = parser.parse_args()
    
    asyncio.run(analyze_user_cli(args.user_id, args.db_url))
