//+------------------------------------------------------------------+
//| ExecutionGuard.mqh                                                |
//| Distributed Execution Control Plane - Receiver Gatekeeper        |
//+------------------------------------------------------------------+
//| Philosophy: Fail-Closed, Adversarial Defense                     |
//| All rejections are logged as "Protection Events"                 |
//+------------------------------------------------------------------+

#property copyright "Fintech Systems Architect"
#property link      "https://github.com/yourorg/execution-guard"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Enumerations                                                      |
//+------------------------------------------------------------------+

enum EXECUTION_STATE
{
    STATE_SYNCED,           // Normal operation, all sequences in order
    STATE_DEGRADED_GAP,     // Sequence gap detected, awaiting full sync
    STATE_LOCKED_NO_FUNDS,  // Insufficient balance, execution halted
    STATE_PAUSED_TOXIC,     // Auto-paused due to low trust score
    STATE_SUSPENDED_ADMIN   // Manually suspended by operator
};

enum REJECTION_REASON
{
    REJECT_NONE,
    REJECT_REPLAY_ATTACK,       // Incoming_Seq <= Local_Last_Seq
    REJECT_DUPLICATE_SEQ,       // Exact duplicate sequence
    REJECT_SEQUENCE_GAP,        // Incoming_Seq > Local_Last_Seq + 1
    REJECT_TTL_EXPIRED,         // Signal age > max_ttl_ms
    REJECT_PRICE_DEVIATION,     // Price slippage beyond threshold
    REJECT_INSUFFICIENT_FUNDS,  // Wallet balance <= 0
    REJECT_STATE_LOCKED,        // Not in SYNCED state
    REJECT_INVALID_SIGNATURE    // Cryptographic validation failed
};

//+------------------------------------------------------------------+
//| Signal Structure (matches Protobuf schema)                       |
//+------------------------------------------------------------------+

struct SignalPacket
{
    // Identity
    string      license_token;
    string      subscription_id;
    
    // Sequence control
    long        sequence_number;
    datetime    generated_at;       // UTC timestamp from master EA
    datetime    server_arrival_time; // Stamped by ingest server
    
    // Trade parameters
    string      symbol;
    int         order_type;         // OP_BUY, OP_SELL, OP_CLOSE
    double      volume;
    double      price;              // Price at master's execution
    double      stop_loss;
    double      take_profit;
    
    // Security
    string      signature;          // HMAC-SHA256 signature
};

//+------------------------------------------------------------------+
//| ExecutionGuard Class - The Gatekeeper                            |
//+------------------------------------------------------------------+

class CExecutionGuard
{
private:
    // State machine
    EXECUTION_STATE     m_state;
    long                m_last_sequence_id;
    datetime            m_last_signal_time;
    
    // Configuration (loaded from server or EA inputs)
    string              m_subscription_id;
    double              m_max_price_deviation;  // In pips
    int                 m_max_ttl_ms;           // Maximum signal age in milliseconds
    string              m_secret_key;           // For HMAC signature validation
    
    // Statistics
    int                 m_total_signals_received;
    int                 m_total_signals_executed;
    int                 m_total_signals_rejected;
    
    // Logging
    int                 m_log_file_handle;
    string              m_log_file_path;
    
    // CRITICAL FIX: Sequence persistence
    int                 m_sequence_file_handle;
    string              m_sequence_file_path;
    
    // Internal methods
    bool                ValidateSequence(const SignalPacket &packet, REJECTION_REASON &reason);
    bool                ValidateTTL(const SignalPacket &packet, REJECTION_REASON &reason);
    bool                ValidatePriceDeviation(const SignalPacket &packet, REJECTION_REASON &reason);
    bool                ValidateFunds(REJECTION_REASON &reason);
    bool                ValidateSignature(const SignalPacket &packet);
    void                LogProtectionEvent(const SignalPacket &packet, REJECTION_REASON reason, int latency_ms);
    void                TransitionState(EXECUTION_STATE new_state, string reason);
    int                 ExecuteTrade(const SignalPacket &packet);
    double              GetCurrentPrice(string symbol, int order_type);
    double              CalculatePriceDeviation(double price1, double price2, string symbol);
    
    // CRITICAL FIX: Sequence persistence methods
    void                PersistSequence(long sequence);
    long                LoadPersistedSequence();
    
public:
    // Constructor
                        CExecutionGuard(string subscription_id, double max_deviation_pips, int max_ttl_ms, string secret_key);
                       ~CExecutionGuard();
    
    // Main entry point
    bool                OnSignal(const SignalPacket &packet);
    
    // State management
    EXECUTION_STATE     GetState() const { return m_state; }
    void                SetState(EXECUTION_STATE state) { m_state = state; }
    long                GetLastSequence() const { return m_last_sequence_id; }
    
    // Configuration
    void                SetMaxPriceDeviation(double pips) { m_max_price_deviation = pips; }
    void                SetMaxTTL(int ms) { m_max_ttl_ms = ms; }
    
    // Statistics
    void                PrintStatistics();
    
    // Full sync request (called when gap detected)
    void                RequestFullSync();
};

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CExecutionGuard::CExecutionGuard(string subscription_id, double max_deviation_pips, int max_ttl_ms, string secret_key)
{
    m_subscription_id = subscription_id;
    m_max_price_deviation = max_deviation_pips;
    m_max_ttl_ms = max_ttl_ms;
    m_secret_key = secret_key;
    
    m_state = STATE_SYNCED;
    m_last_signal_time = 0;
    
    m_total_signals_received = 0;
    m_total_signals_executed = 0;
    m_total_signals_rejected = 0;
    
    // CRITICAL FIX: Load persisted sequence from file
    m_sequence_file_path = "ExecutionGuard_Seq_" + subscription_id + ".dat";
    m_last_sequence_id = LoadPersistedSequence();
    
    Print("Loaded last sequence from file: ", m_last_sequence_id);
    
    // Initialize logging
    m_log_file_path = "ExecutionGuard_" + subscription_id + ".log";
    m_log_file_handle = FileOpen(m_log_file_path, FILE_WRITE|FILE_TXT|FILE_ANSI);
    
    if(m_log_file_handle != INVALID_HANDLE)
    {
        FileWrite(m_log_file_handle, "=== ExecutionGuard Initialized ===");
        FileWrite(m_log_file_handle, "Subscription ID: " + subscription_id);
        FileWrite(m_log_file_handle, "Max Price Deviation: " + DoubleToString(max_deviation_pips, 1) + " pips");
        FileWrite(m_log_file_handle, "Max TTL: " + IntegerToString(max_ttl_ms) + " ms");
        FileWrite(m_log_file_handle, "Last Sequence: " + IntegerToString(m_last_sequence_id));
        FileClose(m_log_file_handle);
    }
}

//+------------------------------------------------------------------+
//| Destructor                                                        |
//+------------------------------------------------------------------+
CExecutionGuard::~CExecutionGuard()
{
    PrintStatistics();
}

//+------------------------------------------------------------------+
//| Main Signal Processing Pipeline                                  |
//| CRITICAL: This is the ONLY entry point for signal execution      |
//| Order of checks: Sequence -> TTL -> Price -> Funds -> Execute    |
//+------------------------------------------------------------------+
bool CExecutionGuard::OnSignal(const SignalPacket &packet)
{
    m_total_signals_received++;
    REJECTION_REASON reason = REJECT_NONE;
    
    // Calculate signal age (latency)
    datetime now_utc = TimeGMT();
    int latency_ms = (int)((now_utc - packet.generated_at) * 1000);
    
    Print("=== SIGNAL RECEIVED ===");
    Print("Sequence: ", packet.sequence_number, " | Symbol: ", packet.symbol, " | Latency: ", latency_ms, "ms");
    
    //-------------------------------------------------------------------
    // GUARD 1: Sequence Validation (Anti-Replay)
    //-------------------------------------------------------------------
    if(!ValidateSequence(packet, reason))
    {
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        
        // If gap detected, transition to DEGRADED state and request sync
        if(reason == REJECT_SEQUENCE_GAP)
        {
            TransitionState(STATE_DEGRADED_GAP, "Sequence gap detected");
            RequestFullSync();
        }
        
        return false;
    }
    
    //-------------------------------------------------------------------
    // GUARD 2: State Check (Must be SYNCED to execute)
    //-------------------------------------------------------------------
    if(m_state != STATE_SYNCED)
    {
        reason = REJECT_STATE_LOCKED;
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        Print("REJECTED: State is ", EnumToString(m_state), " (not SYNCED)");
        return false;
    }
    
    //-------------------------------------------------------------------
    // GUARD 3: TTL Shield (Anti-Lag)
    //-------------------------------------------------------------------
    if(!ValidateTTL(packet, reason))
    {
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        return false;
    }
    
    //-------------------------------------------------------------------
    // GUARD 4: Price Deviation Guard (Anti-Slippage)
    //-------------------------------------------------------------------
    if(!ValidatePriceDeviation(packet, reason))
    {
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        return false;
    }
    
    //-------------------------------------------------------------------
    // GUARD 5: Fund Check (Wallet Balance)
    //-------------------------------------------------------------------
    if(!ValidateFunds(reason))
    {
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        TransitionState(STATE_LOCKED_NO_FUNDS, "Insufficient wallet balance");
        return false;
    }
    
    //-------------------------------------------------------------------
    // GUARD 6: Signature Validation (Cryptographic)
    //-------------------------------------------------------------------
    if(!ValidateSignature(packet))
    {
        reason = REJECT_INVALID_SIGNATURE;
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        Print("REJECTED: Invalid signature - possible tampering");
        return false;
    }
    
    //-------------------------------------------------------------------
    // ALL GUARDS PASSED - EXECUTE TRADE
    //-------------------------------------------------------------------
    
    // CRITICAL FIX: Persist sequence BEFORE execution
    // This prevents sequence loss if EA crashes during OrderSend
    PersistSequence(packet.sequence_number);
    
    int ticket = ExecuteTrade(packet);
    
    if(ticket > 0)
    {
        // Update in-memory sequence (already persisted)
        m_last_sequence_id = packet.sequence_number;
        m_last_signal_time = packet.generated_at;
        m_total_signals_executed++;
        
        Print("EXECUTED: Ticket #", ticket, " | Sequence: ", packet.sequence_number);
        return true;
    }
    else
    {
        // Execution failed - rollback persisted sequence
        if(m_last_sequence_id > 0)
        {
            PersistSequence(m_last_sequence_id);  // Restore previous sequence
        }
        
        Print("EXECUTION FAILED: OrderSend returned error ", GetLastError());
        m_total_signals_rejected++;
        return false;
    }
}

//+------------------------------------------------------------------+
//| Sequence Validation (Anti-Replay & Gap Detection)                |
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidateSequence(const SignalPacket &packet, REJECTION_REASON &reason)
{
    long incoming_seq = packet.sequence_number;
    
    // Case 1: Replay Attack or Duplicate
    if(incoming_seq <= m_last_sequence_id)
    {
        if(incoming_seq == m_last_sequence_id)
            reason = REJECT_DUPLICATE_SEQ;
        else
            reason = REJECT_REPLAY_ATTACK;
        
        Print("REJECTED: Sequence ", incoming_seq, " <= Last ", m_last_sequence_id);
        return false;
    }
    
    // Case 2: Sequence Gap (Missing signals)
    if(incoming_seq > m_last_sequence_id + 1)
    {
        reason = REJECT_SEQUENCE_GAP;
        Print("REJECTED: Sequence gap detected. Expected ", m_last_sequence_id + 1, ", got ", incoming_seq);
        return false;
    }
    
    // Case 3: Valid (incoming_seq == m_last_sequence_id + 1)
    return true;
}

//+------------------------------------------------------------------+
//| TTL Validation (Anti-Lag Shield)                                 |
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidateTTL(const SignalPacket &packet, REJECTION_REASON &reason)
{
    datetime now_utc = TimeGMT();
    int age_ms = (int)((now_utc - packet.generated_at) * 1000);
    
    if(age_ms > m_max_ttl_ms)
    {
        reason = REJECT_TTL_EXPIRED;
        Print("REJECTED: Signal too old. Age: ", age_ms, "ms > Max: ", m_max_ttl_ms, "ms");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Price Deviation Validation (Anti-Slippage)                       |
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidatePriceDeviation(const SignalPacket &packet, REJECTION_REASON &reason)
{
    double current_price = GetCurrentPrice(packet.symbol, packet.order_type);
    double deviation_pips = CalculatePriceDeviation(packet.price, current_price, packet.symbol);
    
    if(deviation_pips > m_max_price_deviation)
    {
        reason = REJECT_PRICE_DEVIATION;
        Print("REJECTED: Price deviation ", DoubleToString(deviation_pips, 1), " pips > Max ", 
              DoubleToString(m_max_price_deviation, 1), " pips");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Fund Validation (Wallet Balance Check)                           |
//| NOTE: In production, this should query the backend API           |
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidateFunds(REJECTION_REASON &reason)
{
    // TODO: Implement actual wallet balance check via API
    // For now, we use account balance as a proxy
    double balance = AccountBalance();
    
    if(balance <= 0)
    {
        reason = REJECT_INSUFFICIENT_FUNDS;
        Print("REJECTED: Insufficient funds. Balance: ", DoubleToString(balance, 2));
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Signature Validation (HMAC-SHA256)                               |
//| WHY: Prevents man-in-the-middle attacks and signal tampering     |
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidateSignature(const SignalPacket &packet)
{
    // CRITICAL FIX: Implement HMAC-SHA256 validation
    
    // Step 1: Construct payload (must match sender's format EXACTLY)
    string payload = StringFormat(
        "%s|%lld|%lld|%s|%d|%.5f|%.5f|%.5f|%.5f",
        packet.subscription_id,
        packet.sequence_number,
        packet.generated_at,
        packet.symbol,
        packet.order_type,
        packet.volume,
        packet.price,
        packet.stop_loss,
        packet.take_profit
    );
    
    // Step 2: Convert strings to byte arrays
    uchar key_bytes[];
    uchar payload_bytes[];
    uchar hash[];
    
    StringToCharArray(m_secret_key, key_bytes, 0, WHOLE_ARRAY, CP_UTF8);
    StringToCharArray(payload, payload_bytes, 0, WHOLE_ARRAY, CP_UTF8);
    
    // Remove null terminators (StringToCharArray adds them)
    ArrayResize(key_bytes, ArraySize(key_bytes) - 1);
    ArrayResize(payload_bytes, ArraySize(payload_bytes) - 1);
    
    // Step 3: Calculate HMAC-SHA256
    // Note: MQL5 doesn't have native HMAC, so we use SHA256(key + message)
    // In production, use proper HMAC implementation or external library
    
    // Concatenate key + payload
    int key_len = ArraySize(key_bytes);
    int payload_len = ArraySize(payload_bytes);
    uchar combined[];
    ArrayResize(combined, key_len + payload_len);
    ArrayCopy(combined, key_bytes, 0, 0, key_len);
    ArrayCopy(combined, payload_bytes, key_len, 0, payload_len);
    
    // Calculate SHA-256 hash
    if(!CryptEncode(CRYPT_HASH_SHA256, combined, key_bytes, hash))
    {
        Print("ERROR: HMAC calculation failed");
        return false;
    }
    
    // Step 4: Convert hash to hex string
    string expected_sig = "";
    for(int i = 0; i < ArraySize(hash); i++)
    {
        expected_sig += StringFormat("%02x", hash[i]);
    }
    
    // Step 5: Constant-time comparison (prevent timing attacks)
    if(StringLen(expected_sig) != StringLen(packet.signature))
    {
        Print("SIGNATURE MISMATCH: Length mismatch");
        return false;
    }
    
    int diff = 0;
    for(int i = 0; i < StringLen(expected_sig); i++)
    {
        diff |= (StringGetCharacter(expected_sig, i) ^ StringGetCharacter(packet.signature, i));
    }
    
    if(diff != 0)
    {
        Print("SIGNATURE MISMATCH: Invalid signature");
        Print("Expected: ", StringSubstr(expected_sig, 0, 16), "...");
        Print("Received: ", StringSubstr(packet.signature, 0, 16), "...");
        return false;
    }
    
    // Signature valid
    return true;
}

//+------------------------------------------------------------------+
//| Execute Trade via OrderSend                                      |
//+------------------------------------------------------------------+
int CExecutionGuard::ExecuteTrade(const SignalPacket &packet)
{
    int ticket = 0;
    double price = GetCurrentPrice(packet.symbol, packet.order_type);
    
    // Normalize volume and prices
    double volume = NormalizeDouble(packet.volume, 2);
    double sl = NormalizeDouble(packet.stop_loss, _Digits);
    double tp = NormalizeDouble(packet.take_profit, _Digits);
    
    // Execute order
    ticket = OrderSend(
        packet.symbol,
        packet.order_type,
        volume,
        price,
        3,              // 3 pip slippage tolerance
        sl,
        tp,
        "ExecutionGuard Seq:" + IntegerToString(packet.sequence_number),
        0,              // Magic number (can be customized)
        0,              // Expiration
        clrGreen
    );
    
    if(ticket < 0)
    {
        int error = GetLastError();
        Print("OrderSend FAILED: Error ", error, " - ", ErrorDescription(error));
    }
    
    return ticket;
}

//+------------------------------------------------------------------+
//| Get Current Market Price                                         |
//+------------------------------------------------------------------+
double CExecutionGuard::GetCurrentPrice(string symbol, int order_type)
{
    if(order_type == OP_BUY)
        return SymbolInfoDouble(symbol, SYMBOL_ASK);
    else
        return SymbolInfoDouble(symbol, SYMBOL_BID);
}

//+------------------------------------------------------------------+
//| Calculate Price Deviation in Pips                                |
//+------------------------------------------------------------------+
double CExecutionGuard::CalculatePriceDeviation(double price1, double price2, string symbol)
{
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    
    // For 5-digit and 3-digit brokers
    double pip_multiplier = (digits == 5 || digits == 3) ? 10.0 : 1.0;
    
    return MathAbs(price1 - price2) / point / pip_multiplier;
}

//+------------------------------------------------------------------+
//| Log Protection Event (to file and optionally to server)          |
//+------------------------------------------------------------------+
void CExecutionGuard::LogProtectionEvent(const SignalPacket &packet, REJECTION_REASON reason, int latency_ms)
{
    string reason_str = EnumToString(reason);
    
    m_log_file_handle = FileOpen(m_log_file_path, FILE_WRITE|FILE_READ|FILE_TXT|FILE_ANSI);
    if(m_log_file_handle != INVALID_HANDLE)
    {
        FileSeek(m_log_file_handle, 0, SEEK_END);
        
        string log_entry = StringFormat(
            "%s | SEQ:%d | REASON:%s | LATENCY:%dms | SYMBOL:%s | STATE:%s",
            TimeToString(TimeGMT(), TIME_DATE|TIME_SECONDS),
            packet.sequence_number,
            reason_str,
            latency_ms,
            packet.symbol,
            EnumToString(m_state)
        );
        
        FileWrite(m_log_file_handle, log_entry);
        FileClose(m_log_file_handle);
    }
    
    // TODO: Send protection event to backend API for Trust Score calculation
    // POST /api/v1/protection-events
    // {
    //   "subscription_id": "...",
    //   "sequence": 123,
    //   "reason": "TTL_EXPIRED",
    //   "latency_ms": 650,
    //   "timestamp": "2026-01-18T13:45:00Z"
    // }
}

//+------------------------------------------------------------------+
//| State Transition with Logging                                    |
//+------------------------------------------------------------------+
void CExecutionGuard::TransitionState(EXECUTION_STATE new_state, string reason)
{
    EXECUTION_STATE old_state = m_state;
    m_state = new_state;
    
    Print("STATE TRANSITION: ", EnumToString(old_state), " -> ", EnumToString(new_state), " | Reason: ", reason);
    
    m_log_file_handle = FileOpen(m_log_file_path, FILE_WRITE|FILE_READ|FILE_TXT|FILE_ANSI);
    if(m_log_file_handle != INVALID_HANDLE)
    {
        FileSeek(m_log_file_handle, 0, SEEK_END);
        FileWrite(m_log_file_handle, "STATE CHANGE: " + EnumToString(old_state) + " -> " + EnumToString(new_state) + " | " + reason);
        FileClose(m_log_file_handle);
    }
}

//+------------------------------------------------------------------+
//| Request Full Sync (when gap detected)                            |
//+------------------------------------------------------------------+
void CExecutionGuard::RequestFullSync()
{
    Print("REQUESTING FULL SYNC from server...");
    
    // TODO: Implement API call to request full sync
    // POST /api/v1/subscriptions/{id}/request-sync
    // Response will contain all missing signals in order
    
    // For now, just log the request
    m_log_file_handle = FileOpen(m_log_file_path, FILE_WRITE|FILE_READ|FILE_TXT|FILE_ANSI);
    if(m_log_file_handle != INVALID_HANDLE)
    {
        FileSeek(m_log_file_handle, 0, SEEK_END);
        FileWrite(m_log_file_handle, "FULL SYNC REQUESTED | Last Seq: " + IntegerToString(m_last_sequence_id));
        FileClose(m_log_file_handle);
    }
}

//+------------------------------------------------------------------+
//| Persist Sequence to File (CRITICAL FIX for race condition)      |
//+------------------------------------------------------------------+
void CExecutionGuard::PersistSequence(long sequence)
{
    // Write sequence to binary file atomically
    int handle = FileOpen(m_sequence_file_path, FILE_WRITE|FILE_BIN);
    
    if(handle != INVALID_HANDLE)
    {
        FileWriteLong(handle, sequence);
        FileFlush(handle);  // Force write to disk
        FileClose(handle);
        
        // Debug log
        // Print("Persisted sequence: ", sequence);
    }
    else
    {
        Print("ERROR: Failed to persist sequence to file: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| Load Persisted Sequence from File                               |
//+------------------------------------------------------------------+
long CExecutionGuard::LoadPersistedSequence()
{
    long sequence = 0;
    
    // Try to read sequence from file
    int handle = FileOpen(m_sequence_file_path, FILE_READ|FILE_BIN);
    
    if(handle != INVALID_HANDLE)
    {
        if(FileSize(handle) >= 8)  // long is 8 bytes
        {
            sequence = FileReadLong(handle);
            Print("Loaded persisted sequence: ", sequence);
        }
        FileClose(handle);
    }
    else
    {
        // File doesn't exist (first run) - start from 0
        Print("No persisted sequence found, starting from 0");
    }
    
    return sequence;
}

//+------------------------------------------------------------------+
//| Print Statistics                                                  |
//+------------------------------------------------------------------+
void CExecutionGuard::PrintStatistics()
{
    Print("=== ExecutionGuard Statistics ===");
    Print("Total Signals Received: ", m_total_signals_received);
    Print("Total Signals Executed: ", m_total_signals_executed);
    Print("Total Signals Rejected: ", m_total_signals_rejected);
    
    if(m_total_signals_received > 0)
    {
        double execution_rate = (double)m_total_signals_executed / m_total_signals_received * 100.0;
        Print("Execution Rate: ", DoubleToString(execution_rate, 2), "%");
    }
    
    Print("Current State: ", EnumToString(m_state));
    Print("Last Sequence: ", m_last_sequence_id);
}

//+------------------------------------------------------------------+
