import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import imaplib
import email
from email.header import decode_header
import pyttsx3
import urllib.request
import urllib.parse
import json
from datetime import datetime
import time
import threading
from queue import Queue
import re

# Initialize text-to-speech engine
engine = pyttsx3.init()

# ===================== CONFIGURATION =====================
# User 1: Henry
USER1 = {
    "name": "Henry Makande",
    "email": "henrymakande@gmail.com",
    "password": "vccq hhgt girv qygz",  # App-specific password
    "telegram_bot_token": "8520084934:AAHe4JjL0wlQKmHdh4TbTnpoGFonQi-bGaY",
    "telegram_chat_id": "7274538950",
    "monitored_senders": [
        "jenturiosoco@gmail.com",
        "info@nukahgps.com",
        "alerts@stackoverflow.com",
        "updates@medium.com",
        "kaizenamante365@gmail.com"

    ],
    "check_interval": 60  # Check every 60 seconds for new emails
}

# User 2: Sarah (Example - replace with actual credentials)
USER2 = {
    "name": "Jenturio Soco Johnson",
    "email": "jenturiosoco@gmail.com",
    "password": "user2_app_password",
    "telegram_bot_token": "USER2_BOT_TOKEN_HERE",
    "telegram_chat_id": "USER2_CHAT_ID_HERE",
    "monitored_senders": [
        "client1@business.com",
        "newsletter@tech.com",
        "support@service.com",
        "billing@company.com"
    ],
    "check_interval": 60
}

# User 3: Michael (Example - replace with actual credentials)
USER3 = {
    "name": "Sante Kulanaga",
    "email": "santekulanga@gmail.com",
    "password": "",
    "telegram_bot_token": "8462713200:AAECnEh1XQdVS5lQu9W3H68aMF4lFoyGVEI",
    "telegram_chat_id": "1780092289",
    "monitored_senders": [
        "henrymakande@gmail.com",
        "info@nukahgps.com",
        "bndalama@nukahgps.com",
        "elnathandmomba@gmail.com"
    ],
    "check_interval": 60
}

# User 4: Emma (Example - replace with actual credentials)
USER4 = {
    "name": "Emma Wilson",
    "email": "emma.wilson@example.com",
    "password": "user4_app_password",
    "telegram_bot_token": "USER4_BOT_TOKEN_HERE",
    "telegram_chat_id": "USER4_CHAT_ID_HERE",
    "monitored_senders": [
        "updates@social.com",
        "marketing@news.com",
        "events@calendar.com",
        "research@data.com"
    ],
    "check_interval": 60
}

# User 5: David (Example - replace with actual credentials)
USER5 = {
    "name": "David Brown",
    "email": "david.brown@example.com",
    "password": "user5_app_password",
    "telegram_bot_token": "USER5_BOT_TOKEN_HERE",
    "telegram_chat_id": "USER5_CHAT_ID_HERE",
    "monitored_senders": [
        "security@alerts.com",
        "system@notifications.com",
        "backup@storage.com",
        "reports@analytics.com"
    ],
    "check_interval": 60
}

# List of all users
ALL_USERS = [USER1, USER2, USER3, USER4, USER5]

# Track processed emails to avoid duplicates
processed_emails = {}
for user in ALL_USERS:
    processed_emails[user["email"]] = set()

# ===================== EMAIL PROCESSING FUNCTIONS =====================

def extract_important_parts(email_body):
    """Extract important parts from email body"""
    if not email_body:
        return "No content available"
    
    # Clean the body
    body = email_body.strip()
    
    # Look for important sections (common patterns)
    important_sections = []
    
    # Check for greeting/salutation
    greeting_patterns = [
        r'Dear\s+[A-Za-z\s,]+[:,\n]',
        r'Hello\s+[A-Za-z\s,]+[:,\n]',
        r'Hi\s+[A-Za-z\s,]+[:,\n]',
        r'Greetings\s*[:,\n]'
    ]
    
    # Check for action items/important markers
    action_patterns = [
        r'(?i)(urgent|important|action required|attention needed)',
        r'(?i)(please\s+(respond|reply|take action))',
        r'(?i)(deadline|due date)[:\s]*(\d+[/-]\d+[/-]\d+|tomorrow|today)',
        r'(?i)(meeting|call|appointment)[:\s]*(\d+[/:]\d+\s*(?:AM|PM)?)',
        r'\$\s*\d+(?:,\d+)*(?:\.\d+)?',  # Money amounts
        r'\d+\s*%',  # Percentages
    ]
    
    # Check for contact information
    contact_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone numbers
        r'(?i)contact.*:\s*[\w\s@.-]+',
    ]
    
    # Find the main message (first 200-500 characters usually contain key info)
    if len(body) > 500:
        # Try to find the main content (skip long quoted/reply sections)
        lines = body.split('\n')
        main_content = []
        in_quoted_section = False
        
        for line in lines[:50]:  # Check first 50 lines
            if line.strip().startswith('>') or line.strip().startswith('On ') and 'wrote:' in line:
                in_quoted_section = True
                continue
            
            if not in_quoted_section and line.strip():
                main_content.append(line.strip())
                if len(' '.join(main_content)) > 300:
                    break
        
        if main_content:
            extracted = ' '.join(main_content)
        else:
            # Fallback to first 300 characters
            extracted = body[:300] + '...'
    else:
        extracted = body
    
    # Clean up the extracted text
    extracted = re.sub(r'\s+', ' ', extracted)  # Replace multiple spaces/newlines
    extracted = extracted.strip()
    
    # Add important markers if found
    important_found = []
    for pattern in action_patterns:
        matches = re.findall(pattern, extracted, re.IGNORECASE)
        if matches:
            important_found.extend(matches)
    
    if important_found:
        extracted = "🚨 IMPORTANT: " + extracted
    
    return extracted

def format_email_for_telegram(msg, user_name):
    """Format email message for Telegram notification"""
    # Decode subject
    subject_header = decode_header(msg["Subject"]) if msg["Subject"] else [("No Subject", "utf-8")]
    subject = ""
    for part, encoding in subject_header:
        if isinstance(part, bytes):
            subject += part.decode(encoding if encoding else 'utf-8', errors='ignore')
        else:
            subject += str(part)
    
    # Get sender info
    from_header = msg.get('From', 'Unknown Sender')
    to_header = msg.get('To', 'Unknown Recipient')
    date_header = msg.get('Date', 'Unknown Date')
    
    # Extract sender name and email
    sender_name = from_header
    sender_email = from_header
    
    # Try to parse name/email from From header
    if '<' in from_header and '>' in from_header:
        match = re.search(r'([^<]+)<([^>]+)>', from_header)
        if match:
            sender_name = match.group(1).strip()
            sender_email = match.group(2).strip()
    
    # Get email body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body_bytes = part.get_payload(decode=True)
                    if body_bytes:
                        body = body_bytes.decode('utf-8', errors='ignore')
                        break
                except:
                    continue
    else:
        try:
            body_bytes = msg.get_payload(decode=True)
            if body_bytes:
                body = body_bytes.decode('utf-8', errors='ignore')
        except:
            body = ""
    
    # Extract important parts from body
    important_content = extract_important_parts(body)
    
    # Format Telegram message
    telegram_msg = f"""📨 *NEW EMAIL ALERT* 📨

*Recipient:* {user_name}
*From:* {sender_name}
*Email:* `{sender_email}`
*Date:* {date_header}
*Subject:* {subject}

*📝 CONTENT:*
{important_content}

---
💡 *Email sent to:* {to_header}"""

    # Truncate if too long (Telegram has 4096 character limit)
    if len(telegram_msg) > 4000:
        telegram_msg = telegram_msg[:3970] + "\n\n... (message truncated)"
    
    return telegram_msg, {
        'subject': subject,
        'sender': sender_email,
        'sender_name': sender_name,
        'date': date_header,
        'body_preview': important_content[:200]
    }

# ===================== CORE FUNCTIONS =====================

def notify_speech(speech):
    """Text-to-speech notification"""
    print(f"🔊 Speaking: {speech[:50]}...")
    engine.say(speech)
    engine.runAndWait()

def send_to_telegram(bot_token, chat_id, message, parse_mode="Markdown"):
    """Send message to Telegram"""
    if not bot_token or bot_token.endswith("_HERE"):
        print(f"⚠️ Telegram not configured for this user")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Prepare data
        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True,
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                print(f"✓ Telegram message sent")
                return True
            else:
                error_desc = result.get('description', 'Unknown error')
                print(f"✗ Telegram error: {error_desc}")
                return False
                
    except Exception as e:
        print(f"✗ Telegram connection error: {e}")
        return False

def check_new_emails(user_config):
    """Check and forward new emails for a single user"""
    user_name = user_config["name"]
    user_email = user_config["email"]
    user_password = user_config["password"]
    monitored_senders = user_config["monitored_senders"]
    bot_token = user_config["telegram_bot_token"]
    chat_id = user_config["telegram_chat_id"]
    
    print(f"\n{'='*60}")
    print(f"🔍 CHECKING NEW EMAILS: {user_name}")
    print(f"📧 Account: {user_email}")
    print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    if not user_password or user_password.endswith("_password"):
        print(f"⚠️ Password not configured for {user_name}")
        return []
    
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user_email, user_password)
        mail.select("inbox")
        
        new_emails_found = []
        
        # Check each monitored sender
        for sender in monitored_senders:
            print(f"\n   🔎 Checking: {sender}")
            
            # Search for UNSEEN emails from this sender
            status, data = mail.search(None, f'(UNSEEN FROM "{sender}")')
            
            if status != "OK":
                print(f"   ❌ Search failed for {sender}")
                continue
            
            email_ids = data[0].split() if data[0] else []
            
            if not email_ids:
                print(f"   📭 No new emails")
                continue
            
            print(f"   🔔 Found {len(email_ids)} new email(s)")
            
            # Process each new email
            for email_id in email_ids:
                email_id_str = email_id.decode()
                
                # Check if we already processed this email
                email_key = f"{user_email}_{sender}_{email_id_str}"
                if email_key in processed_emails[user_email]:
                    print(f"   ⏭️ Already processed email {email_id_str}")
                    continue
                
                # Fetch the email
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                
                if status != "OK":
                    print(f"   ❌ Failed to fetch email {email_id_str}")
                    continue
                
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Format and send to Telegram
                telegram_msg, email_info = format_email_for_telegram(msg, user_name)
                
                # Send to Telegram
                if send_to_telegram(bot_token, chat_id, telegram_msg):
                    print(f"   ✅ Forwarded email: {email_info['subject'][:50]}...")
                    
                    # Add to processed emails
                    processed_emails[user_email].add(email_key)
                    new_emails_found.append(email_info)
                    
                    # Speech notification
                    speech_msg = f"New email from {email_info['sender_name']}. Subject: {email_info['subject'][:50]}"
                    notify_speech(speech_msg)
                else:
                    print(f"   ❌ Failed to send to Telegram")
        
        # Mark emails as read (optional - comment out if you want to keep as unread)
        if new_emails_found:
            try:
                # You can add code here to mark emails as read if desired
                # mail.store(email_id, '+FLAGS', '\\Seen')
                pass
            except:
                pass
        
        mail.logout()
        
        # Send summary if new emails were found
        if new_emails_found:
            summary_msg = f"""📊 *EMAIL CHECK SUMMARY* for {user_name}

✅ Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ Found: {len(new_emails_found)} new email(s)
✅ All new emails have been forwarded

---
💡 *Next check in {user_config.get('check_interval', 60)} seconds*"""
            
            send_to_telegram(bot_token, chat_id, summary_msg)
        
        print(f"\n✅ {user_name}: Check complete. Found {len(new_emails_found)} new emails")
        return new_emails_found
        
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        print(f"❌ Email error for {user_name}: {error_msg}")
        
        # Send error to Telegram
        error_message = f"""❌ *EMAIL ERROR* for {user_name}

*Error:* {error_msg[:200]}
*Time:* {datetime.now().strftime('%H:%M:%S')}

Please check your email configuration."""
        
        send_to_telegram(bot_token, chat_id, error_message)
        return []
        
    except Exception as e:
        print(f"❌ General error for {user_name}: {e}")
        return []

def continuous_email_monitoring():
    """Continuous monitoring for new emails for all users"""
    print(f"🚀 STARTING CONTINUOUS EMAIL MONITORING")
    print(f"👥 Users: {len(ALL_USERS)}")
    print("="*60)
    
    notify_speech("Starting continuous email monitoring for all users")
    
    # Create individual threads for each user
    threads = []
    stop_event = threading.Event()
    
    def monitor_user(user_config):
        """Monitor emails for a single user"""
        user_name = user_config["name"]
        interval = user_config.get("check_interval", 60)
        
        print(f"👤 Starting monitor for {user_name} (check every {interval}s)")
        
        # Send startup notification
        startup_msg = f"""🚀 *EMAIL MONITOR STARTED*

👤 *User:* {user_name}
📧 *Account:* {user_config['email']}
⏰ *Check interval:* {interval} seconds
🕒 *Started at:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

I will notify you of all new emails from:
{chr(10).join(f'• {sender}' for sender in user_config['monitored_senders'])}"""
        
        send_to_telegram(
            user_config["telegram_bot_token"],
            user_config["telegram_chat_id"],
            startup_msg
        )
        
        while not stop_event.is_set():
            try:
                print(f"\n🔍 {datetime.now().strftime('%H:%M:%S')} - Checking {user_name}")
                new_emails = check_new_emails(user_config)
                
                if new_emails:
                    print(f"   ✅ Found {len(new_emails)} new email(s)")
                
            except Exception as e:
                print(f"   ❌ Error monitoring {user_name}: {e}")
            
            # Wait for next check
            for _ in range(interval):
                if stop_event.is_set():
                    break
                time.sleep(1)
        
        # Send stop notification
        stop_msg = f"""🛑 *EMAIL MONITOR STOPPED*

👤 *User:* {user_name}
🕒 *Stopped at:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Email monitoring has been stopped."""
        
        send_to_telegram(
            user_config["telegram_bot_token"],
            user_config["telegram_chat_id"],
            stop_msg
        )
        
        print(f"👤 Stopped monitor for {user_name}")
    
    # Start monitoring thread for each user
    for user in ALL_USERS:
        if user["email"] and user["password"] and not user["password"].endswith("_password"):
            thread = threading.Thread(target=monitor_user, args=(user,))
            thread.daemon = True
            threads.append(thread)
            thread.start()
            time.sleep(2)  # Stagger thread starts
    
    print(f"\n✅ Started {len(threads)} monitoring threads")
    print("Press Ctrl+C to stop all monitors\n")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all monitors...")
        stop_event.set()
        
        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=5)
        
        print("✅ All monitors stopped")
        notify_speech("Email monitoring stopped for all users")

def user_dashboard():
    """Interactive dashboard to manage users"""
    while True:
        print(f"\n{'='*60}")
        print("📧 REAL-TIME EMAIL FORWARDING SYSTEM")
        print("="*60)
        
        print("\n👥 Available Users:")
        for i, user in enumerate(ALL_USERS, 1):
            status = "✅" if user["email"] and user["password"] and not user["password"].endswith("_password") else "❌"
            telegram_status = "🤖" if user["telegram_bot_token"] and not user["telegram_bot_token"].endswith("_HERE") else "❌"
            print(f"{i}. {status}{telegram_status} {user['name']}")
            print(f"   📧 {user['email']}")
            print(f"   📨 Monitors {len(user['monitored_senders'])} senders")
        
        print("\n📋 Options:")
        print("1. Start CONTINUOUS monitoring (forward new emails in real-time)")
        print("2. Check for new emails NOW (one-time check)")
        print("3. Test specific user's Telegram bot")
        print("4. Clear processed emails cache")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            continuous_email_monitoring()
            
        elif choice == "2":
            print("\nSelect user to check:")
            for i, user in enumerate(ALL_USERS, 1):
                if user["email"] and user["password"] and not user["password"].endswith("_password"):
                    print(f"{i}. {user['name']}")
            
            user_num = input(f"\nSelect user (1-{len(ALL_USERS)}): ").strip()
            try:
                idx = int(user_num) - 1
                if 0 <= idx < len(ALL_USERS):
                    user = ALL_USERS[idx]
                    if user["email"] and user["password"] and not user["password"].endswith("_password"):
                        print(f"\n🔍 Checking new emails for {user['name']}...")
                        check_new_emails(user)
                    else:
                        print("❌ User not properly configured")
                else:
                    print("❌ Invalid user number")
            except:
                print("❌ Invalid input")
            
            input("\nPress Enter to continue...")
            
        elif choice == "3":
            print("\n🤖 Test Telegram Bots:")
            for i, user in enumerate(ALL_USERS, 1):
                if user["telegram_bot_token"] and not user["telegram_bot_token"].endswith("_HERE"):
                    print(f"{i}. {user['name']}")
            
            user_num = input(f"\nSelect user (1-{len(ALL_USERS)}): ").strip()
            try:
                idx = int(user_num) - 1
                if 0 <= idx < len(ALL_USERS):
                    user = ALL_USERS[idx]
                    if user["telegram_bot_token"] and not user["telegram_bot_token"].endswith("_HERE"):
                        test_msg = f"""✅ *TELEGRAM BOT TEST*

👤 *User:* {user['name']}
📧 *Email:* {user['email']}
🕒 *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This is a test message to confirm your Telegram bot is working properly."""
                        
                        if send_to_telegram(user["telegram_bot_token"], user["telegram_chat_id"], test_msg):
                            print("✅ Test message sent successfully!")
                        else:
                            print("❌ Failed to send test message")
                    else:
                        print("❌ Telegram bot not configured")
                else:
                    print("❌ Invalid user number")
            except:
                print("❌ Invalid input")
            
            input("\nPress Enter to continue...")
            
        elif choice == "4":
            confirm = input("Are you sure you want to clear the processed emails cache? (y/n): ").strip().lower()
            if confirm == 'y':
                for user in ALL_USERS:
                    processed_emails[user["email"]] = set()
                print("✅ Processed emails cache cleared")
            else:
                print("❌ Operation cancelled")
            
            input("\nPress Enter to continue...")
            
        elif choice == "5":
            print("\n👋 Exiting...")
            break
            
        else:
            print("❌ Invalid choice")

# ===================== MAIN EXECUTION =====================

if __name__ == "__main__":
    print("="*60)
    print("📧 REAL-TIME EMAIL FORWARDING SYSTEM")
    print("="*60)
    print("🔔 Forwards new emails to Telegram in real-time")
    print("📝 Extracts and sends important email content")
    print("👥 Multi-user support with individual monitoring")
    print("="*60)
    
    # Count active users
    active_users = sum(1 for u in ALL_USERS if u["email"] and u["password"] and not u["password"].endswith("_password"))
    print(f"✅ Active users: {active_users}")
    
    # Initialize processed emails tracking
    for user in ALL_USERS:
        processed_emails[user["email"]] = set()
    
    # Start dashboard
    user_dashboard()