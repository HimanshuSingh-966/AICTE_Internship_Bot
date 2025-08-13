#!/usr/bin/env python3
"""
AICTE Internship Bot - Updated for AJAX Endpoint and Telegram 'Apply' Button
Monitors AICTE internship postings and sends Telegram notifications with direct apply links
"""

import os
import json
import time
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Set
import schedule
from threading import Thread
import signal
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class InternshipBot:
    def __init__(self):
        # Configuration from environment variables
        self.config = {
            'AICTE_URL': os.getenv('AICTE_URL', 'https://internship.aicte-india.org/recentlyposted.php'),
            'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
            'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
            'CHECK_INTERVAL_HOURS': int(os.getenv('CHECK_INTERVAL_HOURS', '1')),
            'SEEN_FILE': 'seen_internships.json',
        }
        
        # Your preferred domains - customize this list
        self.preferred_domains = [
            'data science', 'machine learning', 'artificial intelligence', 'ai', 'ml',
            'data analyst', 'ai/ml'
        ]
        
        # CSS Selectors
        self.selectors = {
            'internship_name': ['.job-title'],
            'company_name': ['.company-name'],
            'stipend': ['.stipend span'],
            'type': ['.wfh span', '.location span'],
            'duration': ['.duration span'],
            'start_date': ['.start-date span'],
            'apply_by': ['.apply-by span']
        }

        # Request headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        self._validate_config()
        
    def _validate_config(self):
        """Validate required configuration"""
        if not self.config['TELEGRAM_BOT_TOKEN']:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        if not self.config['TELEGRAM_CHAT_ID']:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
    
    def fetch_webpage(self, page=1) -> str:
        """Fetch internships HTML from the AICTE AJAX endpoint"""
        try:
            logger.info("🔍 Fetching internship data via AJAX endpoint...")
            url = "https://internship.aicte-india.org/class/class_internship.php"
            data = {
                'action': 'load_internship',
                'location': 'all',
                'internship_type': 'all',
                'internship_stipend': 'all',
                'page': page
            }
            response = requests.post(url, data=data, headers=self.headers, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            html = json_data.get('list', '')
            logger.info(f"✅ Successfully fetched AJAX internships ({len(html)} characters)")
            return html
        except Exception as e:
            logger.error(f"❌ Error fetching internships: {e}")
            raise
    
    def extract_internships(self, html: str) -> list:
        logger.info("📋 Extracting internship data...")
        soup = BeautifulSoup(html, 'html.parser')
        internships = []

        for card in soup.select('.card.internship-item'):
            try:
                name = card.select_one('.job-title')
                name = name.get_text(strip=True) if name else 'N/A'

                company = card.select_one('.company-name')
                company = company.get_text(strip=True) if company else 'N/A'

                # Internship type: prefer .wfh, fallback to .location
                internship_type = card.select_one('.wfh span')
                internship_type = internship_type.get_text(strip=True) if internship_type else 'N/A'

                posted_on = card.select_one('.posted-on span')
                posted_on = posted_on.get_text(strip=True) if posted_on else 'N/A'

                location = card.select_one('.location span')
                location = location.get_text(strip=True) if location else 'N/A'

                duration = card.select_one('.duration span')
                duration = duration.get_text(strip=True) if duration else 'N/A'

                start_date = card.select_one('.start-date span')
                start_date = start_date.get_text(strip=True) if start_date else 'N/A'

                all_stipends = card.select('.stipend span')
                stipend = all_stipends[0].get_text(strip=True) if all_stipends else 'N/A'
                credits = all_stipends[1].get_text(strip=True) if len(all_stipends) > 1 else ''

                openings = card.select_one('.user span')
                openings = openings.get_text(strip=True) if openings else 'N/A'

                apply_by = card.select_one('.apply-by span')
                apply_by = apply_by.get_text(strip=True) if apply_by else 'N/A'

                details_link = card.select_one('a.btn.btn-primary')
                details_url = None
                if details_link:
                    details_href = details_link.get('href')
                    if details_href and isinstance(details_href, str):
                        if details_href.startswith('http'):
                            details_url = details_href
                        else:
                            base_url = "https://internship.aicte-india.org"
                            details_url = base_url + '/' + details_href.lstrip('/')

                internship_id = f"{company}-{name}-{location}-{posted_on}".replace(" ", "_")

                internships.append({
                    'id': internship_id,
                    'name': name,
                    'company': company,
                    'stipend': stipend,
                    'credits': credits,
                    'type': internship_type,
                    'posted_on': posted_on,
                    'location': location,
                    'duration': duration,
                    'start_date': start_date,
                    'openings': openings,
                    'apply_by': apply_by,
                    'details_url': details_url
                })
            except Exception as e:
                logger.error(f"Error parsing internship card: {e}")
                continue

        logger.info(f"✅ Extracted {len(internships)} internships")
        return internships

    def filter_by_domain(self, internships: List[Dict]) -> List[Dict]:
        logger.info("🔍 Filtering by preferred domains...")
        filtered = []

        for internship in internships:
            search_text = f"{internship['name']} {internship['company']} {internship.get('description', '')}".lower()
            
            if any(domain.lower() in search_text for domain in self.preferred_domains):
                filtered.append(internship)
                logger.debug(f"✓ Match: {internship['name']} at {internship['company']}")
            else:
                logger.debug(f"✗ No match: {internship['name']} at {internship['company']}")

        logger.info(f"✅ Found {len(filtered)} matching internships")
        return filtered

    def load_seen_internships(self) -> Set[str]:
        """Load previously seen internship IDs"""
        try:
            if os.path.exists(self.config['SEEN_FILE']):
                with open(self.config['SEEN_FILE'], 'r') as f:
                    data = json.load(f)
                    return set(data)
        except Exception as e:
            logger.warning(f"Could not load seen internships: {e}")
        return set()
    
    def save_seen_internships(self, seen_ids: Set[str]):
        """Save seen internship IDs to file"""
        try:
            # Keep only last 1000 to prevent file from growing too large
            seen_list = list(seen_ids)[-1000:]
            with open(self.config['SEEN_FILE'], 'w') as f:
                json.dump(seen_list, f, indent=2)
            logger.debug(f"Saved {len(seen_list)} seen internship IDs")
        except Exception as e:
            logger.error(f"Could not save seen internships: {e}")
    
    def get_new_internships(self, internships: List[Dict]) -> List[Dict]:
        """Filter out previously seen internships"""
        logger.info("🆕 Checking for new internships...")
        seen = self.load_seen_internships()
        new_internships = [i for i in internships if i['id'] not in seen]
        
        # Add new internship IDs to seen list
        for internship in new_internships:
            seen.add(internship['id'])
        
        self.save_seen_internships(seen)
        
        logger.info(f"🎉 Found {len(new_internships)} new internships")
        return new_internships
    
    def format_telegram_message(self, internship: Dict) -> str:
        """Format internship data for Telegram message"""
        return f"""🚀 *New Internship Alert!*

📋 *Internship:* {internship['name']}
🏢 *Company:* {internship['company']}
💰 *Stipend:* {internship['stipend']}
📍 *Type:* {internship['type']}
⏰ *Duration:* {internship['duration']}
📅 *Start Date:* {internship['start_date']}

🔍 Found: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}

#Internship #AICTE #JobAlert #{internship['company'].replace(' ', '').replace('-', '').replace('_', '')}"""
    
    def send_telegram_message_with_apply(self, internship: Dict) -> bool:
        """Send message to Telegram with an 'Apply' button"""
        try:
            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
            apply_url = internship.get('details_url')
            message = self.format_telegram_message(internship)
            data = {
                'chat_id': self.config['TELEGRAM_CHAT_ID'],
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True,
                'reply_markup': json.dumps({
                    "inline_keyboard": [
                        [{"text": "Apply Now 🚀", "url": apply_url if apply_url else "https://internship.aicte-india.org"}]
                    ]
                })
            }
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"❌ Error sending Telegram message: {e}")
            return False
    
    def send_summary(self, total_found: int, filtered: int, new_count: int):
        """Send summary report"""
        summary_message = f"""📊 *AICTE Internship Bot Summary*

🔍 Total internships found: {total_found}
✅ Matching your domains: {filtered}
🆕 New notifications sent: {new_count}

⏰ Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}

{'🎉 New opportunities above!' if new_count > 0 else '😴 No new internships this time'}"""

        self.send_telegram_message_with_apply({'details_url': None, 'name':'Summary', 'company':'-', 'stipend':'-', 'type':'-', 'duration':'-', 'start_date':'-', 'posted_on':'-', 'location':'-'})
    
    def run_check(self):
        """Main function to check for internships"""
        try:
            logger.info("🚀 Starting AICTE Internship Bot check...")
            start_time = datetime.now()
            
            # Fetch and process internships
            html = self.fetch_webpage()

            with open("fetched_live.html", "w", encoding="utf-8") as f:
                f.write(html)
            all_internships = self.extract_internships(html)
            filtered_internships = self.filter_by_domain(all_internships)
            new_internships = self.get_new_internships(filtered_internships)
            
            # Send notifications for new internships
            sent_count = 0
            for internship in new_internships:
                if self.send_telegram_message_with_apply(internship):
                    sent_count += 1
                    logger.info(f"📤 Sent notification: {internship['name']} at {internship['company']}")
                    if len(new_internships) > 1:
                        time.sleep(2)
                else:
                    logger.error(f"Failed to send notification for: {internship['name']}")
            
            # Send summary
            self.send_summary(len(all_internships), len(filtered_internships), sent_count)
            
            duration = datetime.now() - start_time
            logger.info(f"✅ Check completed successfully in {duration.total_seconds():.2f} seconds")
            logger.info(f"📊 Summary: {len(all_internships)} total, {len(filtered_internships)} filtered, {sent_count} new")
            
        except Exception as e:
            logger.error(f"❌ Bot check failed: {e}")
            error_message = f"""🚨 *AICTE Bot Error*

Error: {str(e)}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}

Please check the logs for more details."""
            self.send_telegram_message_with_apply({'details_url': None, 'name':'Error', 'company':'-', 'stipend':'-', 'type':'-', 'duration':'-', 'start_date':'-', 'posted_on':'-', 'location':'-'})
            raise
    
    def start_scheduler(self):
        """Start the scheduled job"""
        logger.info(f"🕐 Scheduling bot to run every {self.config['CHECK_INTERVAL_HOURS']} hour(s)")
        
        # Schedule the job
        schedule.every(self.config['CHECK_INTERVAL_HOURS']).hours.do(self.run_check)
        
        # Run once immediately for testing
        logger.info("🏃 Running initial check...")
        self.run_check()
        
        # Keep the scheduler running
        logger.info("⏰ Scheduler started. Press Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("🛑 Received shutdown signal. Stopping bot...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        bot = InternshipBot()
        
        # For Render: Run as web service with keep-alive
        if os.getenv('RENDER'):
            logger.info("🌐 Running in Render mode with web server")
            from threading import Thread
            import http.server
            import socketserver
            
            # Start simple HTTP server for Render health checks
            PORT = int(os.getenv('PORT', 10000))
            
            class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'AICTE Internship Bot is running!')
                    
                def log_message(self, format, *args):
                    pass  # Suppress HTTP logs
            
            httpd = socketserver.TCPServer(("", PORT), HealthCheckHandler)
            server_thread = Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()
            
            logger.info(f"🌐 Health check server started on port {PORT}")
            
            # Start the scheduler in the main thread
            bot.start_scheduler()
        else:
            # Run normally
            bot.start_scheduler()
            
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()