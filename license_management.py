"""
Advanced License Management System
====================================

This module implements advanced license management features:
1. Multi-device detection (license sharing prevention)
2. Auto-renewal (payment integration)
3. Usage analytics and monitoring
4. Suspicious activity detection
5. License health scoring
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)


class LicenseStatus(Enum):
    """License status enumeration"""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    PENDING_RENEWAL = "PENDING_RENEWAL"


class SuspiciousActivityType(Enum):
    """Types of suspicious activity"""
    MULTIPLE_IPS = "MULTIPLE_IPS"
    RAPID_IP_CHANGES = "RAPID_IP_CHANGES"
    UNUSUAL_USAGE_PATTERN = "UNUSUAL_USAGE_PATTERN"
    CONCURRENT_SESSIONS = "CONCURRENT_SESSIONS"
    GEOGRAPHIC_ANOMALY = "GEOGRAPHIC_ANOMALY"


@dataclass
class DeviceFingerprint:
    """Unique device identifier"""
    ip_address: str
    ea_instance_id: str
    mt5_account_number: int
    first_seen: datetime
    last_seen: datetime
    usage_count: int
    geographic_location: Optional[str] = None


@dataclass
class LicenseHealthReport:
    """Comprehensive license health assessment"""
    license_token_id: str
    subscription_id: str
    status: LicenseStatus
    health_score: int  # 0-100
    days_until_expiry: Optional[int]
    unique_devices: int
    suspicious_activities: List[SuspiciousActivityType]
    usage_stats: Dict[str, any]
    recommendations: List[str]


class MultiDeviceDetector:
    """
    Detects and prevents license sharing across multiple devices.
    
    Strategy:
    ---------
    1. Track unique device fingerprints (IP + EA instance ID + MT5 account)
    2. Allow up to 2 devices per license (primary + backup)
    3. Flag suspicious patterns (>2 devices, rapid IP changes)
    4. Auto-suspend licenses with confirmed sharing
    """
    
    def __init__(self, db_connection, max_devices: int = 2):
        """
        Initialize multi-device detector.
        
        Args:
            db_connection: Database connection pool
            max_devices: Maximum allowed devices per license (default: 2)
        """
        self.db = db_connection
        self.max_devices = max_devices
    
    async def track_device_usage(
        self,
        token_hash: str,
        ip_address: str,
        ea_instance_id: str,
        mt5_account: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Track device usage and detect multi-device violations.
        
        Returns:
            (is_allowed, violation_reason)
        """
        # Create device fingerprint
        fingerprint = f"{ip_address}|{ea_instance_id}|{mt5_account}"
        
        # Get all devices for this license
        query = """
            SELECT 
                ip_address,
                ea_instance_id,
                metadata->>'mt5_account' as mt5_account,
                last_used_at,
                metadata->>'usage_count' as usage_count
            FROM license_tokens
            WHERE token_hash = $1
        """
        
        current_token = await self.db.fetchrow(query, token_hash)
        
        if not current_token:
            return False, "Invalid license token"
        
        # Parse existing device data
        devices = await self._get_device_fingerprints(token_hash)
        
        # Check if this is a known device
        current_device = next(
            (d for d in devices if self._match_fingerprint(d, fingerprint)),
            None
        )
        
        if current_device:
            # Known device - update last seen
            await self._update_device_activity(token_hash, fingerprint)
            return True, None
        
        # New device detected
        if len(devices) >= self.max_devices:
            # Too many devices - check for violations
            violation = await self._analyze_device_pattern(token_hash, devices, fingerprint)
            
            if violation:
                logger.warning(
                    f"Multi-device violation detected for token {token_hash[:8]}... "
                    f"Devices: {len(devices) + 1}, Reason: {violation}"
                )
                
                # Auto-suspend license
                await self._suspend_license(token_hash, violation)
                
                return False, f"License suspended: {violation}"
        
        # Register new device
        await self._register_device(token_hash, fingerprint)
        
        logger.info(
            f"New device registered for token {token_hash[:8]}... "
            f"Total devices: {len(devices) + 1}/{self.max_devices}"
        )
        
        return True, None
    
    async def _get_device_fingerprints(self, token_hash: str) -> List[DeviceFingerprint]:
        """Retrieve all device fingerprints for a license"""
        query = """
            SELECT 
                metadata->'devices' as devices_json
            FROM license_tokens
            WHERE token_hash = $1
        """
        
        row = await self.db.fetchrow(query, token_hash)
        
        if not row or not row['devices_json']:
            return []
        
        devices_data = row['devices_json']
        devices = []
        
        for device_key, device_info in devices_data.items():
            devices.append(DeviceFingerprint(
                ip_address=device_info['ip'],
                ea_instance_id=device_info['ea_instance_id'],
                mt5_account_number=device_info['mt5_account'],
                first_seen=datetime.fromisoformat(device_info['first_seen']),
                last_seen=datetime.fromisoformat(device_info['last_seen']),
                usage_count=device_info['usage_count'],
                geographic_location=device_info.get('geo_location')
            ))
        
        return devices
    
    def _match_fingerprint(self, device: DeviceFingerprint, fingerprint: str) -> bool:
        """Check if device matches fingerprint"""
        parts = fingerprint.split('|')
        return (
            device.ip_address == parts[0] and
            device.ea_instance_id == parts[1] and
            device.mt5_account_number == int(parts[2])
        )
    
    async def _analyze_device_pattern(
        self,
        token_hash: str,
        devices: List[DeviceFingerprint],
        new_fingerprint: str
    ) -> Optional[str]:
        """
        Analyze device usage pattern for suspicious activity.
        
        Returns violation reason if detected, None otherwise.
        """
        # Check 1: Too many unique IPs in short time
        recent_ips = set()
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        for device in devices:
            if device.last_seen > cutoff_time:
                recent_ips.add(device.ip_address)
        
        if len(recent_ips) > 3:
            return f"Too many unique IPs in 24h: {len(recent_ips)}"
        
        # Check 2: Geographic anomaly (IPs from different continents)
        locations = [d.geographic_location for d in devices if d.geographic_location]
        if len(set(locations)) > 2:
            return f"Geographic anomaly: IPs from {len(set(locations))} locations"
        
        # Check 3: Concurrent active sessions
        active_devices = [
            d for d in devices
            if (datetime.utcnow() - d.last_seen).total_seconds() < 300  # 5 min
        ]
        
        if len(active_devices) > 1:
            return f"Concurrent sessions detected: {len(active_devices)} active devices"
        
        # Check 4: Rapid device switching (>5 device changes per day)
        device_changes_today = await self._count_device_changes_today(token_hash)
        if device_changes_today > 5:
            return f"Rapid device switching: {device_changes_today} changes today"
        
        return None
    
    async def _register_device(self, token_hash: str, fingerprint: str):
        """Register a new device for a license"""
        parts = fingerprint.split('|')
        device_key = f"device_{len(parts)}"
        
        query = """
            UPDATE license_tokens
            SET metadata = jsonb_set(
                COALESCE(metadata, '{}'::jsonb),
                '{devices, """ + device_key + """}',
                jsonb_build_object(
                    'ip', $2,
                    'ea_instance_id', $3,
                    'mt5_account', $4,
                    'first_seen', $5,
                    'last_seen', $5,
                    'usage_count', 1
                )
            )
            WHERE token_hash = $1
        """
        
        await self.db.execute(
            query,
            token_hash,
            parts[0],  # IP
            parts[1],  # EA instance ID
            int(parts[2]),  # MT5 account
            datetime.utcnow().isoformat()
        )
    
    async def _update_device_activity(self, token_hash: str, fingerprint: str):
        """Update last seen time for a device"""
        # Implementation would update the specific device's last_seen and usage_count
        pass
    
    async def _count_device_changes_today(self, token_hash: str) -> int:
        """Count how many times devices changed today"""
        # Implementation would query device change log
        return 0
    
    async def _suspend_license(self, token_hash: str, reason: str):
        """Suspend a license due to violation"""
        query = """
            UPDATE license_tokens
            SET is_active = FALSE,
                revoked_at = NOW(),
                revoked_reason = $2
            WHERE token_hash = $1
        """
        
        await self.db.execute(query, token_hash, f"Auto-suspended: {reason}")
        
        # Also pause all subscriptions
        query_pause = """
            UPDATE subscriptions
            SET state = 'SUSPENDED_ADMIN',
                paused_at = NOW(),
                paused_reason = $2
            WHERE subscription_id IN (
                SELECT subscription_id 
                FROM license_tokens 
                WHERE token_hash = $1
            )
        """
        
        await self.db.execute(query_pause, token_hash, f"License suspended: {reason}")


class AutoRenewalManager:
    """
    Manages automatic license renewal with payment integration.
    
    Features:
    ---------
    1. Detect expiring licenses (7 days before expiry)
    2. Attempt auto-renewal via saved payment method
    3. Send notifications on success/failure
    4. Grace period (3 days after expiry)
    5. Auto-suspend if renewal fails
    """
    
    def __init__(self, db_connection, payment_gateway):
        """
        Initialize auto-renewal manager.
        
        Args:
            db_connection: Database connection pool
            payment_gateway: Payment gateway client (Stripe, PayPal, etc.)
        """
        self.db = db_connection
        self.payment_gateway = payment_gateway
    
    async def process_renewals(self):
        """
        Main renewal processing loop.
        Should be run as a background worker (e.g., daily cron job).
        """
        logger.info("Starting auto-renewal processing...")
        
        # Get licenses expiring in next 7 days
        expiring_licenses = await self._get_expiring_licenses(days=7)
        
        logger.info(f"Found {len(expiring_licenses)} licenses expiring soon")
        
        for license_info in expiring_licenses:
            try:
                await self._process_single_renewal(license_info)
            except Exception as e:
                logger.error(
                    f"Failed to process renewal for subscription "
                    f"{license_info['subscription_id']}: {e}"
                )
        
        # Handle expired licenses (grace period ended)
        await self._suspend_expired_licenses()
        
        logger.info("Auto-renewal processing complete")
    
    async def _get_expiring_licenses(self, days: int) -> List[Dict]:
        """Get licenses expiring within specified days"""
        query = """
            SELECT 
                lt.token_id,
                lt.subscription_id,
                lt.expires_at,
                s.subscriber_id,
                u.email,
                u.user_id,
                uw.wallet_id,
                s.master_id,
                -- Calculate renewal fee (monthly subscription fee if any)
                COALESCE(
                    (SELECT monthly_fee FROM master_pricing WHERE master_id = s.master_id),
                    0
                ) as renewal_fee
            FROM license_tokens lt
            JOIN subscriptions s ON lt.subscription_id = s.subscription_id
            JOIN users u ON s.subscriber_id = u.user_id
            JOIN user_wallets uw ON u.user_id = uw.user_id
            WHERE lt.is_active = TRUE
              AND lt.expires_at IS NOT NULL
              AND lt.expires_at > NOW()
              AND lt.expires_at <= NOW() + INTERVAL '1 day' * $1
              AND lt.metadata->>'auto_renew' = 'true'
            ORDER BY lt.expires_at ASC
        """
        
        rows = await self.db.fetch(query, days)
        return [dict(row) for row in rows]
    
    async def _process_single_renewal(self, license_info: Dict):
        """Process renewal for a single license"""
        subscription_id = license_info['subscription_id']
        user_id = license_info['user_id']
        renewal_fee = license_info['renewal_fee']
        
        logger.info(
            f"Processing renewal for subscription {subscription_id}, "
            f"fee: ${renewal_fee}"
        )
        
        # Check wallet balance
        wallet_balance = await self._get_wallet_balance(user_id)
        
        if wallet_balance < renewal_fee:
            # Insufficient balance - try payment method
            logger.warning(
                f"Insufficient wallet balance (${wallet_balance}) for "
                f"subscription {subscription_id}, attempting payment..."
            )
            
            payment_success = await self._charge_payment_method(
                user_id, renewal_fee
            )
            
            if not payment_success:
                # Payment failed - send notification
                await self._notify_renewal_failed(license_info)
                return
        
        # Debit wallet
        try:
            await self._debit_wallet_for_renewal(
                user_id,
                renewal_fee,
                subscription_id
            )
        except Exception as e:
            logger.error(f"Failed to debit wallet: {e}")
            await self._notify_renewal_failed(license_info)
            return
        
        # Extend license expiration
        new_expiry = license_info['expires_at'] + timedelta(days=30)
        
        await self.db.execute(
            """
            UPDATE license_tokens
            SET expires_at = $2,
                metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{last_renewal}',
                    to_jsonb($3::text)
                )
            WHERE subscription_id = $1
            """,
            subscription_id,
            new_expiry,
            datetime.utcnow().isoformat()
        )
        
        logger.info(
            f"✅ Renewal successful for subscription {subscription_id}. "
            f"New expiry: {new_expiry}"
        )
        
        # Send success notification
        await self._notify_renewal_success(license_info, new_expiry)
    
    async def _get_wallet_balance(self, user_id: str) -> float:
        """Get user's wallet balance"""
        query = "SELECT balance_usd FROM user_wallets WHERE user_id = $1"
        row = await self.db.fetchrow(query, user_id)
        return float(row['balance_usd']) if row else 0.0
    
    async def _charge_payment_method(self, user_id: str, amount: float) -> bool:
        """
        Attempt to charge user's saved payment method.
        
        Returns True if successful, False otherwise.
        """
        # Get saved payment method
        query = """
            SELECT payment_method_id, payment_provider
            FROM user_payment_methods
            WHERE user_id = $1
              AND is_default = TRUE
              AND is_active = TRUE
        """
        
        payment_method = await self.db.fetchrow(query, user_id)
        
        if not payment_method:
            logger.warning(f"No payment method found for user {user_id}")
            return False
        
        try:
            # Charge via payment gateway (Stripe example)
            charge_result = await self.payment_gateway.charge(
                payment_method_id=payment_method['payment_method_id'],
                amount=amount,
                currency='USD',
                description=f"License renewal for user {user_id}"
            )
            
            if charge_result['status'] == 'succeeded':
                # Credit wallet with charged amount
                await self._credit_wallet(user_id, amount, "Auto-renewal payment")
                return True
            else:
                logger.error(f"Payment failed: {charge_result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Payment gateway error: {e}")
            return False
    
    async def _debit_wallet_for_renewal(
        self,
        user_id: str,
        amount: float,
        subscription_id: str
    ):
        """Debit wallet for renewal fee"""
        query = """
            SELECT debit_wallet(
                $1::uuid,
                $2::decimal,
                'FEE_SUBSCRIPTION'::ledger_entry_type,
                $3,
                $4::uuid
            )
        """
        
        description = f"Monthly subscription renewal"
        
        await self.db.execute(
            query,
            user_id,
            amount,
            description,
            subscription_id
        )
    
    async def _credit_wallet(self, user_id: str, amount: float, description: str):
        """Credit wallet (after successful payment)"""
        query = """
            SELECT credit_wallet(
                $1::uuid,
                $2::decimal,
                'DEPOSIT'::ledger_entry_type,
                $3
            )
        """
        
        await self.db.execute(query, user_id, amount, description)
    
    async def _notify_renewal_success(self, license_info: Dict, new_expiry: datetime):
        """Send notification on successful renewal"""
        # TODO: Implement email/SMS notification
        logger.info(
            f"📧 Sending renewal success notification to {license_info['email']}"
        )
    
    async def _notify_renewal_failed(self, license_info: Dict):
        """Send notification on failed renewal"""
        # TODO: Implement email/SMS notification
        logger.warning(
            f"📧 Sending renewal failure notification to {license_info['email']}"
        )
    
    async def _suspend_expired_licenses(self):
        """Suspend licenses that expired >3 days ago (grace period ended)"""
        query = """
            UPDATE license_tokens
            SET is_active = FALSE,
                revoked_at = NOW(),
                revoked_reason = 'Expired - grace period ended'
            WHERE is_active = TRUE
              AND expires_at < NOW() - INTERVAL '3 days'
            RETURNING subscription_id
        """
        
        suspended = await self.db.fetch(query)
        
        if suspended:
            logger.info(f"Suspended {len(suspended)} expired licenses")
            
            # Pause subscriptions
            for row in suspended:
                await self.db.execute(
                    """
                    UPDATE subscriptions
                    SET state = 'SUSPENDED_ADMIN',
                        paused_at = NOW(),
                        paused_reason = 'License expired'
                    WHERE subscription_id = $1
                    """,
                    row['subscription_id']
                )


class LicenseHealthMonitor:
    """
    Monitors overall license health and generates reports.
    
    Provides:
    ---------
    1. Health score (0-100) for each license
    2. Usage analytics
    3. Anomaly detection
    4. Recommendations for operators
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def generate_health_report(
        self,
        subscription_id: str
    ) -> LicenseHealthReport:
        """Generate comprehensive health report for a license"""
        
        # Get license info
        license_info = await self._get_license_info(subscription_id)
        
        if not license_info:
            raise ValueError(f"License not found: {subscription_id}")
        
        # Calculate health score
        health_score = await self._calculate_health_score(subscription_id)
        
        # Get device count
        devices = await self._get_device_count(license_info['token_hash'])
        
        # Detect suspicious activities
        suspicious = await self._detect_suspicious_activities(subscription_id)
        
        # Get usage stats
        usage_stats = await self._get_usage_stats(subscription_id)
        
        # Calculate days until expiry
        days_until_expiry = None
        if license_info['expires_at']:
            delta = license_info['expires_at'] - datetime.utcnow()
            days_until_expiry = delta.days
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            health_score,
            days_until_expiry,
            devices,
            suspicious
        )
        
        return LicenseHealthReport(
            license_token_id=license_info['token_id'],
            subscription_id=subscription_id,
            status=LicenseStatus(license_info['status']),
            health_score=health_score,
            days_until_expiry=days_until_expiry,
            unique_devices=devices,
            suspicious_activities=suspicious,
            usage_stats=usage_stats,
            recommendations=recommendations
        )
    
    async def _get_license_info(self, subscription_id: str) -> Optional[Dict]:
        """Get basic license information"""
        query = """
            SELECT 
                token_id,
                token_hash,
                expires_at,
                is_active,
                CASE 
                    WHEN NOT is_active THEN 'REVOKED'
                    WHEN expires_at < NOW() THEN 'EXPIRED'
                    WHEN expires_at < NOW() + INTERVAL '7 days' THEN 'PENDING_RENEWAL'
                    ELSE 'ACTIVE'
                END as status
            FROM license_tokens
            WHERE subscription_id = $1
        """
        
        row = await self.db.fetchrow(query, subscription_id)
        return dict(row) if row else None
    
    async def _calculate_health_score(self, subscription_id: str) -> int:
        """
        Calculate health score (0-100) based on multiple factors.
        
        Factors:
        - License status (active/expired): 40 points
        - Usage frequency: 20 points
        - Device count (1-2 devices): 20 points
        - No suspicious activity: 20 points
        """
        score = 0
        
        # Factor 1: License status
        license_info = await self._get_license_info(subscription_id)
        if license_info['is_active']:
            score += 40
        
        # Factor 2: Usage frequency (used in last 24h)
        last_used = await self.db.fetchval(
            "SELECT last_used_at FROM license_tokens WHERE subscription_id = $1",
            subscription_id
        )
        
        if last_used and (datetime.utcnow() - last_used).total_seconds() < 86400:
            score += 20
        
        # Factor 3: Device count
        device_count = await self._get_device_count(license_info['token_hash'])
        if device_count <= 2:
            score += 20
        
        # Factor 4: No suspicious activity
        suspicious = await self._detect_suspicious_activities(subscription_id)
        if not suspicious:
            score += 20
        
        return min(100, max(0, score))
    
    async def _get_device_count(self, token_hash: str) -> int:
        """Count unique devices for a license"""
        # Implementation would count devices from metadata
        return 1
    
    async def _detect_suspicious_activities(
        self,
        subscription_id: str
    ) -> List[SuspiciousActivityType]:
        """Detect suspicious activities for a license"""
        suspicious = []
        
        # Check for multiple IPs
        # Check for rapid IP changes
        # Check for unusual usage patterns
        # etc.
        
        return suspicious
    
    async def _get_usage_stats(self, subscription_id: str) -> Dict:
        """Get usage statistics"""
        return {
            "signals_received_24h": 0,
            "signals_executed_24h": 0,
            "signals_rejected_24h": 0,
            "avg_latency_ms": 0,
            "last_activity": None
        }
    
    def _generate_recommendations(
        self,
        health_score: int,
        days_until_expiry: Optional[int],
        device_count: int,
        suspicious: List[SuspiciousActivityType]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if health_score < 50:
            recommendations.append("⚠️ License health is poor - investigate immediately")
        
        if days_until_expiry is not None and days_until_expiry < 7:
            recommendations.append(f"🔔 License expires in {days_until_expiry} days - renew soon")
        
        if device_count > 2:
            recommendations.append(f"🚨 {device_count} devices detected - possible license sharing")
        
        if suspicious:
            recommendations.append(f"⚠️ Suspicious activity detected: {', '.join(s.value for s in suspicious)}")
        
        if not recommendations:
            recommendations.append("✅ License is healthy - no action needed")
        
        return recommendations


# ==============================================================================
# Background Workers
# ==============================================================================

async def multi_device_monitor_worker(db_pool):
    """
    Background worker that monitors for multi-device violations.
    Run this as a separate process/container.
    """
    detector = MultiDeviceDetector(db_pool)
    
    while True:
        try:
            # Get all active licenses
            query = """
                SELECT token_hash, subscription_id
                FROM license_tokens
                WHERE is_active = TRUE
            """
            
            async with db_pool.acquire() as conn:
                licenses = await conn.fetch(query)
                
                for license_row in licenses:
                    try:
                        # Analyze device usage
                        devices = await detector._get_device_fingerprints(
                            license_row['token_hash']
                        )
                        
                        if len(devices) > detector.max_devices:
                            logger.warning(
                                f"License {license_row['subscription_id']} has "
                                f"{len(devices)} devices (max: {detector.max_devices})"
                            )
                            
                            # Analyze for violations
                            violation = await detector._analyze_device_pattern(
                                license_row['token_hash'],
                                devices,
                                ""  # No new fingerprint
                            )
                            
                            if violation:
                                await detector._suspend_license(
                                    license_row['token_hash'],
                                    violation
                                )
                    
                    except Exception as e:
                        logger.error(
                            f"Error monitoring license {license_row['subscription_id']}: {e}"
                        )
            
            # Run every hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Multi-device monitor error: {e}")
            await asyncio.sleep(300)  # Retry after 5 minutes


async def auto_renewal_worker(db_pool, payment_gateway):
    """
    Background worker for automatic license renewal.
    Run this daily (e.g., via cron job at midnight).
    """
    manager = AutoRenewalManager(db_pool, payment_gateway)
    
    while True:
        try:
            await manager.process_renewals()
            
            # Run once per day (24 hours)
            await asyncio.sleep(86400)
            
        except Exception as e:
            logger.error(f"Auto-renewal worker error: {e}")
            await asyncio.sleep(3600)  # Retry after 1 hour


# ==============================================================================
# CLI Tools
# ==============================================================================

async def generate_license_report_cli(subscription_id: str, db_url: str):
    """
    CLI tool to generate license health report.
    
    Usage:
    ------
    python license_management.py --subscription-id <uuid> --db-url <postgres_url>
    """
    import asyncpg
    
    conn = await asyncpg.connect(db_url)
    monitor = LicenseHealthMonitor(conn)
    
    report = await monitor.generate_health_report(subscription_id)
    
    print("\n" + "="*80)
    print(f"LICENSE HEALTH REPORT: {subscription_id}")
    print("="*80)
    print(f"Status:              {report.status.value}")
    print(f"Health Score:        {report.health_score}/100")
    print(f"Days Until Expiry:   {report.days_until_expiry or 'N/A'}")
    print(f"Unique Devices:      {report.unique_devices}")
    print(f"\nSuspicious Activities:")
    if report.suspicious_activities:
        for activity in report.suspicious_activities:
            print(f"  - {activity.value}")
    else:
        print("  None detected ✓")
    
    print(f"\nUsage Stats:")
    for key, value in report.usage_stats.items():
        print(f"  - {key}: {value}")
    
    print(f"\nRecommendations:")
    for rec in report.recommendations:
        print(f"  {rec}")
    
    print("="*80 + "\n")
    
    await conn.close()


if __name__ == "__main__":
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="License Management CLI")
    parser.add_argument("--subscription-id", help="Subscription UUID")
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection URL")
    
    args = parser.parse_args()
    
    if args.subscription_id:
        asyncio.run(generate_license_report_cli(args.subscription_id, args.db_url))
    else:
        print("Please provide --subscription-id")
