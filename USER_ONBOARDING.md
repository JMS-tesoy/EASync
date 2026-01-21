# User Onboarding Guide - Distributed Execution Control Plane

## 🎯 Overview

This guide walks you through the complete process of joining the platform as a **subscriber** who wants to copy trades from master traders.

---

## 👥 User Roles

Before we begin, understand there are **two types of users**:

| Role | Description | What They Do |
|------|-------------|--------------|
| **Master Trader** | Experienced trader | Generates trade signals that others copy |
| **Subscriber** | Follower/Copier | Copies trades from master traders automatically |

**This guide is for SUBSCRIBERS** (people who want to copy trades).

---

## 📍 Step-by-Step Journey

```
1. Sign Up → 2. Choose Master → 3. Subscribe → 4. Install EA → 5. Start Copying
   (5 min)     (10 min)         (2 min)        (10 min)       (Automatic)
```

---

## Step 1: Sign Up for an Account

### 🌐 Visit the Platform Website

**URL:** `https://yourplatform.com`

### 📝 Create Your Account

1. Click **"Sign Up"** button
2. Fill in registration form:
   ```
   Email:    your.email@example.com
   Password: ********** (min 8 characters)
   Name:     John Doe
   Country:  United States
   ```
3. Verify your email (check inbox for verification link)
4. Complete profile setup

### 💰 Add Funds to Your Wallet

The platform uses **pre-paid credits** for fees:

1. Go to **"Wallet"** section
2. Click **"Deposit"**
3. Choose payment method:
   - Credit Card
   - Bank Transfer
   - Cryptocurrency
4. Deposit amount: **$100** (recommended minimum)
5. Confirm payment

**What are credits used for?**
- Performance fees (20% of profits above high-water mark)
- Monthly subscription fees (if applicable)
- Platform usage fees

---

## Step 2: Browse & Choose a Master Trader

### 🔍 Explore Master Traders

Navigate to **"Master Traders"** or **"Marketplace"**

You'll see a list of traders with stats:

```
┌─────────────────────────────────────────────────────────┐
│  Master Trader: John Smith (@forex_pro)                 │
│  ⭐⭐⭐⭐⭐ 4.8/5.0 (245 reviews)                          │
│                                                          │
│  📊 Performance (Last 12 Months):                       │
│     Total Return:    +45.2%                             │
│     Win Rate:        68%                                │
│     Max Drawdown:    -12.3%                             │
│     Avg Trade:       +2.1%                              │
│                                                          │
│  💼 Trading Style:                                      │
│     Strategy:        Swing Trading                      │
│     Pairs:           EUR/USD, GBP/USD, USD/JPY          │
│     Risk Level:      Medium                             │
│     Avg Trades/Day:  3-5                                │
│                                                          │
│  💵 Fees:                                               │
│     Performance Fee: 20% (on profits above HWM)         │
│     Monthly Fee:     $0 (free)                          │
│                                                          │
│  👥 Subscribers:     1,247 active                       │
│                                                          │
│  [View Details]  [Subscribe Now]                        │
└─────────────────────────────────────────────────────────┘
```

### 📈 Review Performance History

Click **"View Details"** to see:
- Detailed trade history
- Equity curve chart
- Monthly returns breakdown
- Risk metrics (Sharpe ratio, Sortino ratio)
- Reviews from other subscribers

### ✅ Make Your Decision

Consider:
- **Performance:** Consistent returns over time?
- **Risk:** Drawdown acceptable for you?
- **Style:** Matches your risk tolerance?
- **Reviews:** What do other subscribers say?

---

## Step 3: Subscribe to a Master Trader

### 🎫 Create Subscription

1. Click **"Subscribe Now"** on the master's profile
2. Review subscription terms:
   ```
   Master Trader:     John Smith
   Performance Fee:   20% (on profits above HWM)
   Monthly Fee:       $0
   Min. Deposit:      $500 (recommended)
   Risk Level:        Medium
   ```
3. Configure your settings:
   ```
   Max Price Deviation:  50 pips (default)
   Max Signal Age (TTL): 500ms (default)
   Auto-Pause on Low Trust Score: Enabled
   ```
4. Click **"Confirm Subscription"**

### 🔑 Receive Your License Credentials

**IMPORTANT:** You'll see this screen **ONLY ONCE**:

```
┌─────────────────────────────────────────────────────────┐
│  ✅ Subscription Created Successfully!                  │
│                                                          │
│  📋 SAVE THESE CREDENTIALS (shown only once):           │
│                                                          │
│  Subscription ID:                                       │
│  550e8400-e29b-41d4-a716-446655440000                   │
│                                                          │
│  License Token:                                         │
│  dQw4w9WgXcQ_r7-8N3vZ5kL2mP9xYtBaC1fG4hJ6             │
│                                                          │
│  ⚠️ CRITICAL: Copy these to a safe place!               │
│  You'll need them to configure your EA.                 │
│                                                          │
│  [Copy to Clipboard]  [Download as Text File]           │
└─────────────────────────────────────────────────────────┘
```

**Action:** Click **"Download as Text File"** and save it securely.

---

## Step 4: Install the Subscriber EA

### 📥 Download the EA

1. Go to **"Downloads"** section
2. Click **"Download Subscriber EA"**
3. Save file: `SubscriberEA.ex5` (size: ~50KB)

### 💻 Install in MetaTrader 5

#### Option A: Drag & Drop (Easiest)

1. Open **MetaTrader 5** (MT5)
2. Open **File Explorer**, navigate to downloaded `SubscriberEA.ex5`
3. **Drag** the file into MT5's **Navigator** window
4. Drop it under **"Expert Advisors"** section

#### Option B: Manual Installation

1. Open MT5
2. Click **File → Open Data Folder**
3. Navigate to: `MQL5/Experts/`
4. Copy `SubscriberEA.ex5` into this folder
5. Restart MT5
6. EA appears in **Navigator → Expert Advisors**

### ⚙️ Configure the EA

1. In MT5, open a chart (e.g., EUR/USD)
2. In **Navigator**, find **"SubscriberEA"**
3. **Drag** it onto the chart
4. Configuration window appears:

```
┌─────────────────────────────────────────────────────────┐
│  SubscriberEA - Configuration                           │
│                                                          │
│  📋 License Credentials:                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Subscription ID:                                  │  │
│  │ [550e8400-e29b-41d4-a716-446655440000]           │  │
│  │                                                   │  │
│  │ License Token:                                    │  │
│  │ [dQw4w9WgXcQ_r7-8N3vZ5kL2mP9xYtBaC1fG4hJ6]      │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  🔧 Advanced Settings:                                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Max Price Deviation (pips): [50.0]               │  │
│  │ Max Signal Age (ms):        [500]                │  │
│  │ WebSocket URL:                                   │  │
│  │ [wss://api.yourplatform.com/signals]             │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ☑ Allow Algo Trading                                  │
│  ☑ Allow DLL imports                                    │
│  ☑ Allow WebRequest to: api.yourplatform.com            │
│                                                          │
│  [Cancel]  [OK]                                         │
└─────────────────────────────────────────────────────────┘
```

5. **Paste** your Subscription ID and License Token (from Step 3)
6. Check **"Allow Algo Trading"** ✓
7. Check **"Allow DLL imports"** ✓ (if needed)
8. Check **"Allow WebRequest"** ✓
9. Click **"OK"**

### ✅ Verify EA is Running

You should see:

```
┌─────────────────────────────────────────────────────────┐
│  EUR/USD Chart                                          │
│                                                          │
│  😊 SubscriberEA                    [EA is running]     │
│                                                          │
│  [Price chart here]                                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**In the Experts tab (bottom of MT5):**

```
2026.01.20 20:05:00  SubscriberEA EURUSD,H1: Initializing Subscriber EA...
2026.01.20 20:05:01  SubscriberEA EURUSD,H1: ExecutionGuard initialized successfully
2026.01.20 20:05:01  SubscriberEA EURUSD,H1: Subscription ID: 550e8400-e29b-41d4-a716-446655440000
2026.01.20 20:05:01  SubscriberEA EURUSD,H1: Max Price Deviation: 50.0 pips
2026.01.20 20:05:01  SubscriberEA EURUSD,H1: Max TTL: 500 ms
2026.01.20 20:05:02  SubscriberEA EURUSD,H1: ✅ Connected to signal server
2026.01.20 20:05:02  SubscriberEA EURUSD,H1: ✅ License validated
2026.01.20 20:05:02  SubscriberEA EURUSD,H1: 🎯 Waiting for signals from master...
```

---

## Step 5: Start Copying Trades (Automatic)

### 🎉 You're All Set!

The EA is now **actively monitoring** for signals from your master trader.

### 📊 What Happens Next

When the master trader executes a trade:

```
1. Master EA (Master's MT5)
   ↓ Generates signal
   
2. Ingest Server (Platform)
   ↓ Validates & timestamps
   
3. Redis Streams
   ↓ Distributes to all subscribers
   
4. Your EA (Your MT5)
   ↓ Receives signal
   ↓ ExecutionGuard validates:
      ✓ Sequence number (no replay)
      ✓ Signal age (< 500ms)
      ✓ Price deviation (< 50 pips)
      ✓ Wallet balance (> 0)
      ✓ Signature (HMAC valid)
   ↓ All checks passed
   
5. OrderSend() - Trade Executed! ✅
```

### 📱 Monitor Your Trades

#### In MT5:

**Experts Tab:**
```
2026.01.20 20:15:23  SubscriberEA: === SIGNAL RECEIVED ===
2026.01.20 20:15:23  SubscriberEA: Sequence: 1 | Symbol: EURUSD | Latency: 45ms
2026.01.20 20:15:23  SubscriberEA: ✅ EXECUTED: Ticket #12345678 | Sequence: 1
```

**Trade Tab:**
```
Ticket   Time        Type  Volume  Symbol   Price     S/L       T/P       Profit
12345678 20:15:23   Buy   0.10    EURUSD   1.10000   1.09500   1.10500   +0.00
```

#### On Platform Dashboard:

1. Log in to `https://yourplatform.com`
2. Go to **"My Subscriptions"**
3. View real-time stats:
   ```
   ┌─────────────────────────────────────────────────────┐
   │  Subscription: John Smith (@forex_pro)              │
   │  Status: 🟢 Active                                  │
   │                                                      │
   │  📊 Your Performance (This Month):                 │
   │     Total Profit:      +$125.50                    │
   │     Win Rate:          72%                         │
   │     Trades Executed:   18                          │
   │     Trades Rejected:   2 (TTL expired)             │
   │     Trust Score:       95/100 ✅                   │
   │                                                      │
   │  💰 Fees Paid:                                     │
   │     Performance Fee:   $25.10 (20% of profit)     │
   │     Monthly Fee:       $0.00                       │
   │                                                      │
   │  📈 High-Water Mark:   $125.50                     │
   │     (Next fees only on profit above this)          │
   │                                                      │
   │  [View Trade History]  [Pause Subscription]        │
   └─────────────────────────────────────────────────────┘
   ```

---

## 🛡️ Safety Features (Automatic)

### ExecutionGuard Protections

Your EA automatically rejects trades if:

| Protection | Trigger | What Happens |
|------------|---------|--------------|
| **TTL Shield** | Signal older than 500ms | ❌ Rejected (stale price) |
| **Price Deviation** | Price moved >50 pips | ❌ Rejected (too much slippage) |
| **Sequence Gap** | Missing signals detected | ⚠️ EA pauses, requests sync |
| **No Funds** | Wallet balance = $0 | 🔒 EA locks, no execution |
| **Low Trust Score** | Score drops below 50 | 🚫 Auto-paused by platform |

### Trust Score System

Your account has a **Trust Score (0-100)**:

- **100:** Perfect (no issues)
- **70-99:** Good (minor issues)
- **50-69:** Warning (degraded)
- **<50:** Auto-paused (too many issues)

**Score decreases when:**
- Signals expire (TTL) → -5 points
- Price deviations → -3 points
- Sequence gaps → -20 points

**Score increases when:**
- Successful executions → +1 point
- 24 hours without issues → +10 points

---

## 💡 Common Questions

### Q1: How much money do I need to start?

**Minimum:** $500 in your MT5 account + $100 in platform wallet

**Recommended:** $1,000+ for better risk management

### Q2: Can I copy multiple master traders?

**Yes!** You can subscribe to multiple masters:
- Each subscription needs its own EA instance
- Attach each EA to a different chart
- Each has separate license credentials

### Q3: What if I want to stop copying?

**Option 1: Pause Subscription**
1. Go to platform dashboard
2. Click "Pause Subscription"
3. EA stops receiving signals (existing trades remain open)

**Option 2: Remove EA**
1. Right-click chart in MT5
2. Select "Expert Advisors → Remove"
3. EA stops immediately

### Q4: How are fees calculated?

**Performance Fee (20%):**
- Only charged on **NEW profits** above your high-water mark
- Example:
  ```
  Month 1: +$100 profit → Fee: $20 (20% of $100)
  Month 2: -$50 loss   → Fee: $0 (no profit)
  Month 3: +$150 total → Fee: $10 (20% of $50 new profit above $100 HWM)
  ```

**Monthly Fee:**
- Varies by master trader (some are free, some charge $10-50/month)
- Charged on 1st of each month

### Q5: What if my internet disconnects?

**Short disconnection (<5 min):**
- EA reconnects automatically
- Missed signals are detected (sequence gap)
- EA requests full sync from server

**Long disconnection (>5 min):**
- EA enters DEGRADED_GAP state
- Stops executing new trades
- You must manually restart EA to resync

### Q6: Can I customize trade sizes?

**Currently:** EA copies exact volume from master

**Future feature:** Volume multiplier (e.g., 0.5x, 2x master's volume)

---

## 🚨 Troubleshooting

### Problem: EA shows "License Invalid"

**Solution:**
1. Check you entered correct Subscription ID and License Token
2. Verify subscription is active on platform dashboard
3. Check wallet balance > $0
4. Contact support if issue persists

### Problem: EA not executing trades

**Check:**
1. **Algo Trading enabled?** (Tools → Options → Expert Advisors → "Allow Algo Trading")
2. **EA running?** (Look for smiley face 😊 on chart)
3. **Internet connected?** (Check MT5 connection status)
4. **Trust Score?** (Check dashboard - may be auto-paused)

### Problem: Trades rejected (TTL Expired)

**Causes:**
- Slow internet connection
- VPS latency too high
- Master trader in different timezone

**Solutions:**
- Upgrade to faster VPS (recommended: <50ms ping to server)
- Increase Max TTL setting (e.g., 1000ms)
- Contact support for server location closer to you

---

## 📞 Support

### Need Help?

- **Email:** support@yourplatform.com
- **Live Chat:** Available on platform dashboard
- **Documentation:** https://docs.yourplatform.com
- **Community Forum:** https://forum.yourplatform.com

### Emergency Support

- **Phone:** +1-800-FOREX-HELP
- **WhatsApp:** +1-555-123-4567
- **Available:** 24/7 (Forex markets never sleep!)

---

## 🎓 Next Steps

### Beginner Tips

1. **Start Small:** Begin with minimum deposit, scale up as you gain confidence
2. **Monitor Daily:** Check dashboard daily for first week
3. **Understand Risks:** Past performance ≠ future results
4. **Diversify:** Consider copying 2-3 different masters
5. **Set Limits:** Use MT5's built-in stop-loss and take-profit

### Advanced Features (Coming Soon)

- **Risk Management:** Set max daily loss limits
- **Volume Scaling:** Adjust trade sizes (0.5x, 2x, etc.)
- **Partial Copy:** Only copy certain pairs or trade types
- **Custom Filters:** Add your own entry/exit rules
- **Mobile App:** Monitor and control from your phone

---

## ✅ Checklist: Are You Ready?

Before you start, make sure:

- [ ] Account created and email verified
- [ ] Wallet funded with at least $100
- [ ] Master trader selected and reviewed
- [ ] Subscription created
- [ ] License credentials saved securely
- [ ] MT5 installed and account opened
- [ ] Subscriber EA downloaded and installed
- [ ] EA configured with correct credentials
- [ ] EA running and connected (green smiley face)
- [ ] Dashboard shows subscription as "Active"

**All checked?** 🎉 **You're ready to start copying trades!**

---

**Welcome to the platform! Happy trading! 📈**
