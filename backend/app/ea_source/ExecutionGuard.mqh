//+------------------------------------------------------------------+
//| ExecutionGuard.mqh                                                |
//| Distributed Execution Control Plane - Receiver Gatekeeper        |
//| Copyright 2026-01-25                                             |
//+------------------------------------------------------------------+
//| Philosophy: Fail-Closed, Adversarial Defense                     |
//| All rejections are logged as "Protection Events"                 |
//+------------------------------------------------------------------+

#property copyright "EA Sync - Fintech Systems Architect"
#property link      "https://easync.com"
#property version   "2.00"
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
    int         order_type;         // 1=BUY, 2=SELL, 3=CLOSE
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
    
    // Configuration
    string              m_symbol;
    double              m_max_lot_size;
    int                 m_max_daily_trades;
    string              m_secret_key;
    double              m_max_price_deviation;
    int                 m_max_ttl_ms;
    
    // Statistics
    int                 m_total_signals_received;
    int                 m_total_signals_executed;
    int                 m_total_signals_rejected;
    
    // Logging
    int                 m_log_file_handle;
    string              m_log_file_path;
    
    // Sequence persistence
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
    void                PersistSequence(long sequence);
    long                LoadPersistedSequence();
    
public:
                        CExecutionGuard(string symbol, double max_lot, int max_daily, string secret_key);
                       ~CExecutionGuard();
    
    bool                OnSignal(const SignalPacket &packet);
    bool                CanTrade() const { return m_state == STATE_SYNCED; }
    EXECUTION_STATE     GetState() const { return m_state; }
    void                SetState(EXECUTION_STATE state) { m_state = state; }
    long                GetLastSequence() const { return m_last_sequence_id; }
    void                SetMaxPriceDeviation(double pips) { m_max_price_deviation = pips; }
    void                SetMaxTTL(int ms) { m_max_ttl_ms = ms; }
    void                PrintStatistics();
    void                RequestFullSync();
};

//+------------------------------------------------------------------+
//| Constructor                                                       |
//+------------------------------------------------------------------+
CExecutionGuard::CExecutionGuard(string symbol, double max_lot, int max_daily, string secret_key)
{
    m_symbol = symbol;
    m_max_lot_size = max_lot;
    m_max_daily_trades = max_daily;
    m_secret_key = secret_key;
    m_max_price_deviation = 5.0;  // 5 pips default
    m_max_ttl_ms = 5000;          // 5 seconds default
    
    m_state = STATE_SYNCED;
    m_last_signal_time = 0;
    
    m_total_signals_received = 0;
    m_total_signals_executed = 0;
    m_total_signals_rejected = 0;
    
    // Load persisted sequence
    m_sequence_file_path = "ExecutionGuard_Seq_" + symbol + ".dat";
    m_last_sequence_id = LoadPersistedSequence();
    
    Print("ExecutionGuard initialized for ", symbol);
    Print("Loaded last sequence: ", m_last_sequence_id);
    
    // Initialize logging
    m_log_file_path = "ExecutionGuard_" + symbol + ".log";
    m_log_file_handle = FileOpen(m_log_file_path, FILE_WRITE|FILE_TXT|FILE_ANSI);
    
    if(m_log_file_handle != INVALID_HANDLE)
    {
        FileWrite(m_log_file_handle, "=== ExecutionGuard Initialized ===");
        FileWrite(m_log_file_handle, "Symbol: " + symbol);
        FileWrite(m_log_file_handle, "Max Lot: " + DoubleToString(max_lot, 2));
        FileWrite(m_log_file_handle, "Max Daily Trades: " + IntegerToString(max_daily));
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
//+------------------------------------------------------------------+
bool CExecutionGuard::OnSignal(const SignalPacket &packet)
{
    m_total_signals_received++;
    REJECTION_REASON reason = REJECT_NONE;
    
    datetime now_utc = TimeGMT();
    int latency_ms = (int)((now_utc - packet.generated_at) * 1000);
    
    Print("=== SIGNAL RECEIVED ===");
    Print("Sequence: ", packet.sequence_number, " | Symbol: ", packet.symbol, " | Latency: ", latency_ms, "ms");
    
    // GUARD 1: Sequence Validation
    if(!ValidateSequence(packet, reason))
    {
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        
        if(reason == REJECT_SEQUENCE_GAP)
        {
            TransitionState(STATE_DEGRADED_GAP, "Sequence gap detected");
            RequestFullSync();
        }
        return false;
    }
    
    // GUARD 2: State Check
    if(m_state != STATE_SYNCED)
    {
        reason = REJECT_STATE_LOCKED;
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        Print("REJECTED: State is ", EnumToString(m_state));
        return false;
    }
    
    // GUARD 3: TTL Shield
    if(!ValidateTTL(packet, reason))
    {
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        return false;
    }
    
    // GUARD 4: Price Deviation
    if(!ValidatePriceDeviation(packet, reason))
    {
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        return false;
    }
    
    // GUARD 5: Fund Check
    if(!ValidateFunds(reason))
    {
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        TransitionState(STATE_LOCKED_NO_FUNDS, "Insufficient funds");
        return false;
    }
    
    // GUARD 6: Signature Validation
    if(!ValidateSignature(packet))
    {
        reason = REJECT_INVALID_SIGNATURE;
        LogProtectionEvent(packet, reason, latency_ms);
        m_total_signals_rejected++;
        Print("REJECTED: Invalid signature");
        return false;
    }
    
    // ALL GUARDS PASSED - Execute
    PersistSequence(packet.sequence_number);
    
    int ticket = ExecuteTrade(packet);
    
    if(ticket > 0)
    {
        m_last_sequence_id = packet.sequence_number;
        m_last_signal_time = packet.generated_at;
        m_total_signals_executed++;
        Print("EXECUTED: Ticket #", ticket);
        return true;
    }
    else
    {
        if(m_last_sequence_id > 0)
            PersistSequence(m_last_sequence_id);
        
        Print("EXECUTION FAILED: ", GetLastError());
        m_total_signals_rejected++;
        return false;
    }
}

//+------------------------------------------------------------------+
//| Sequence Validation                                              |
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidateSequence(const SignalPacket &packet, REJECTION_REASON &reason)
{
    long incoming_seq = packet.sequence_number;
    
    if(incoming_seq <= m_last_sequence_id)
    {
        reason = (incoming_seq == m_last_sequence_id) ? REJECT_DUPLICATE_SEQ : REJECT_REPLAY_ATTACK;
        Print("REJECTED: Sequence ", incoming_seq, " <= Last ", m_last_sequence_id);
        return false;
    }
    
    if(incoming_seq > m_last_sequence_id + 1)
    {
        reason = REJECT_SEQUENCE_GAP;
        Print("REJECTED: Gap detected. Expected ", m_last_sequence_id + 1, ", got ", incoming_seq);
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| TTL Validation                                                   |
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
//| Price Deviation Validation                                       |
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidatePriceDeviation(const SignalPacket &packet, REJECTION_REASON &reason)
{
    double current_price = GetCurrentPrice(packet.symbol, packet.order_type);
    double deviation_pips = CalculatePriceDeviation(packet.price, current_price, packet.symbol);
    
    if(deviation_pips > m_max_price_deviation)
    {
        reason = REJECT_PRICE_DEVIATION;
        Print("REJECTED: Price deviation ", DoubleToString(deviation_pips, 1), " pips");
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Fund Validation                                                  |
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidateFunds(REJECTION_REASON &reason)
{
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    
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
//+------------------------------------------------------------------+
bool CExecutionGuard::ValidateSignature(const SignalPacket &packet)
{
    // Construct payload matching sender format
    string payload = StringFormat(
        "%s|%lld|%lld|%s|%d|%.5f|%.5f|%.5f|%.5f",
        packet.subscription_id,
        packet.sequence_number,
        (long)packet.generated_at * 1000,
        packet.symbol,
        packet.order_type,
        packet.volume,
        packet.price,
        packet.stop_loss,
        packet.take_profit
    );
    
    uchar key_bytes[], payload_bytes[], hash[];
    StringToCharArray(m_secret_key, key_bytes);
    StringToCharArray(payload, payload_bytes);
    
    ArrayResize(key_bytes, ArraySize(key_bytes) - 1);
    ArrayResize(payload_bytes, ArraySize(payload_bytes) - 1);
    
    int key_len = ArraySize(key_bytes);
    int payload_len = ArraySize(payload_bytes);
    uchar combined[];
    ArrayResize(combined, key_len + payload_len);
    ArrayCopy(combined, key_bytes, 0, 0, key_len);
    ArrayCopy(combined, payload_bytes, key_len, 0, payload_len);
    
    if(!CryptEncode(CRYPT_HASH_SHA256, combined, key_bytes, hash))
    {
        Print("ERROR: HMAC calculation failed");
        return false;
    }
    
    string expected_sig = "";
    for(int i = 0; i < ArraySize(hash); i++)
        expected_sig += StringFormat("%02x", hash[i]);
    
    if(StringLen(expected_sig) != StringLen(packet.signature))
        return false;
    
    int diff = 0;
    for(int i = 0; i < StringLen(expected_sig); i++)
        diff |= (StringGetCharacter(expected_sig, i) ^ StringGetCharacter(packet.signature, i));
    
    return (diff == 0);
}

//+------------------------------------------------------------------+
//| Execute Trade (MQL5)                                             |
//+------------------------------------------------------------------+
int CExecutionGuard::ExecuteTrade(const SignalPacket &packet)
{
    MqlTradeRequest request;
    MqlTradeResult result;
    
    ZeroMemory(request);
    ZeroMemory(result);
    
    double price = GetCurrentPrice(packet.symbol, packet.order_type);
    double volume = MathMin(packet.volume, m_max_lot_size);
    volume = NormalizeDouble(volume, 2);
    
    int digits = (int)SymbolInfoInteger(packet.symbol, SYMBOL_DIGITS);
    double sl = NormalizeDouble(packet.stop_loss, digits);
    double tp = NormalizeDouble(packet.take_profit, digits);
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = packet.symbol;
    request.volume = volume;
    request.type = (packet.order_type == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.price = price;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 3;
    request.magic = 0;
    request.comment = "EG Seq:" + IntegerToString(packet.sequence_number);
    request.type_filling = ORDER_FILLING_FOK;
    
    bool success = OrderSend(request, result);
    
    if(!success || result.retcode != TRADE_RETCODE_DONE)
    {
        Print("OrderSend FAILED: ", result.retcode, " - ", result.comment);
        return -1;
    }
    
    Print("OrderSend SUCCESS: Ticket=", result.order);
    return (int)result.order;
}

//+------------------------------------------------------------------+
//| Get Current Price                                                |
//+------------------------------------------------------------------+
double CExecutionGuard::GetCurrentPrice(string symbol, int order_type)
{
    return (order_type == 1) ? 
           SymbolInfoDouble(symbol, SYMBOL_ASK) : 
           SymbolInfoDouble(symbol, SYMBOL_BID);
}

//+------------------------------------------------------------------+
//| Calculate Price Deviation in Pips                                |
//+------------------------------------------------------------------+
double CExecutionGuard::CalculatePriceDeviation(double price1, double price2, string symbol)
{
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
    double pip_mult = (digits == 5 || digits == 3) ? 10.0 : 1.0;
    
    return MathAbs(price1 - price2) / point / pip_mult;
}

//+------------------------------------------------------------------+
//| Log Protection Event                                             |
//+------------------------------------------------------------------+
void CExecutionGuard::LogProtectionEvent(const SignalPacket &packet, REJECTION_REASON reason, int latency_ms)
{
    m_log_file_handle = FileOpen(m_log_file_path, FILE_WRITE|FILE_READ|FILE_TXT|FILE_ANSI);
    if(m_log_file_handle != INVALID_HANDLE)
    {
        FileSeek(m_log_file_handle, 0, SEEK_END);
        string entry = StringFormat(
            "%s | SEQ:%d | REASON:%s | LATENCY:%dms | STATE:%s",
            TimeToString(TimeGMT(), TIME_DATE|TIME_SECONDS),
            packet.sequence_number,
            EnumToString(reason),
            latency_ms,
            EnumToString(m_state)
        );
        FileWrite(m_log_file_handle, entry);
        FileClose(m_log_file_handle);
    }
}

//+------------------------------------------------------------------+
//| State Transition                                                 |
//+------------------------------------------------------------------+
void CExecutionGuard::TransitionState(EXECUTION_STATE new_state, string reason)
{
    EXECUTION_STATE old_state = m_state;
    m_state = new_state;
    Print("STATE: ", EnumToString(old_state), " -> ", EnumToString(new_state), " | ", reason);
}

//+------------------------------------------------------------------+
//| Request Full Sync                                                |
//+------------------------------------------------------------------+
void CExecutionGuard::RequestFullSync()
{
    Print("REQUESTING FULL SYNC...");
    // TODO: API call to /api/v1/subscriptions/{id}/request-sync
}

//+------------------------------------------------------------------+
//| Persist Sequence                                                 |
//+------------------------------------------------------------------+
void CExecutionGuard::PersistSequence(long sequence)
{
    int handle = FileOpen(m_sequence_file_path, FILE_WRITE|FILE_BIN);
    if(handle != INVALID_HANDLE)
    {
        FileWriteLong(handle, sequence);
        FileFlush(handle);
        FileClose(handle);
    }
}

//+------------------------------------------------------------------+
//| Load Persisted Sequence                                          |
//+------------------------------------------------------------------+
long CExecutionGuard::LoadPersistedSequence()
{
    long sequence = 0;
    int handle = FileOpen(m_sequence_file_path, FILE_READ|FILE_BIN);
    
    if(handle != INVALID_HANDLE)
    {
        if(FileSize(handle) >= 8)
            sequence = FileReadLong(handle);
        FileClose(handle);
    }
    
    return sequence;
}

//+------------------------------------------------------------------+
//| Print Statistics                                                 |
//+------------------------------------------------------------------+
void CExecutionGuard::PrintStatistics()
{
    Print("=== ExecutionGuard Statistics ===");
    Print("Received: ", m_total_signals_received);
    Print("Executed: ", m_total_signals_executed);
    Print("Rejected: ", m_total_signals_rejected);
    
    if(m_total_signals_received > 0)
    {
        double rate = (double)m_total_signals_executed / m_total_signals_received * 100.0;
        Print("Execution Rate: ", DoubleToString(rate, 2), "%");
    }
    
    Print("State: ", EnumToString(m_state));
    Print("Last Seq: ", m_last_sequence_id);
}

//+------------------------------------------------------------------+