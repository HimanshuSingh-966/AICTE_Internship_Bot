#!/usr/bin/env python3
import os
import json
import time
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Set, Optional
import schedule
from threading import Thread
import signal
import sys
from dotenv import load_dotenv
from abc import ABC, abstractmethod
import hashlib
from urllib.parse import urljoin, quote

# Load environment variables
load_dotenv()

# Configure loggings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class InternshipScraper(ABC):
    """Abstract base class for internship scrapers"""
    
    def __init__(self, name: str, preferred_domains: List[str]):
        self.name = name
        self.preferred_domains = preferred_domains
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    @abstractmethod
    def fetch_internships(self) -> List[Dict]:
        """Fetch internships from the platform"""
        pass
    
    def filter_by_domain(self, internships: List[Dict]) -> List[Dict]:
        """Filter internships by preferred domains"""
        logger.info(f"🔍 [{self.name}] Filtering by preferred domains...")
        filtered = []

        for internship in internships:
            search_text = f"{internship['name']} {internship['company']} {internship.get('description', '')}".lower()
            
            if any(domain.lower() in search_text for domain in self.preferred_domains):
                filtered.append(internship)
                logger.debug(f"✓ [{self.name}] Match: {internship['name']} at {internship['company']}")
            else:
                logger.debug(f"✗ [{self.name}] No match: {internship['name']} at {internship['company']}")

        logger.info(f"✅ [{self.name}] Found {len(filtered)} matching internships")
        return filtered

class AICTEScraper(InternshipScraper):
    """AICTE Internship Scraper"""
    
    def __init__(self, preferred_domains: List[str]):
        super().__init__("AICTE", preferred_domains)
        self.base_url = "https://internship.aicte-india.org/recentlyposted.php"
        self.ajax_url = "https://internship.aicte-india.org/class/class_internship.php"
    
    def fetch_internships(self) -> List[Dict]:
        """Fetch internships from AICTE"""
        try:
            logger.info(f"🔍 [{self.name}] Fetching internship data...")
            data = {
                'action': 'load_internship',
                'location': 'all',
                'internship_type': 'all',
                'internship_stipend': 'all',
                'page': 1
            }
            response = requests.post(self.ajax_url, data=data, headers=self.headers, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            html = json_data.get('list', '')
            
            return self._parse_html(html)
        except Exception as e:
            logger.error(f"❌ [{self.name}] Error fetching internships: {e}")
            return []
    
    def _parse_html(self, html: str) -> List[Dict]:
        """Parse AICTE HTML and extract internships"""
        soup = BeautifulSoup(html, 'html.parser')
        internships = []

        for card in soup.select('.card.internship-item'):
            try:
                name = card.select_one('.job-title')
                name = name.get_text(strip=True) if name else 'N/A'

                company = card.select_one('.company-name')
                company = company.get_text(strip=True) if company else 'N/A'

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

                apply_by = card.select_one('.apply-by span')
                apply_by = apply_by.get_text(strip=True) if apply_by else 'N/A'

                details_link = card.select_one('a.btn.btn-primary')
                details_url = None
                if details_link:
                    details_href = details_link.get('href')
                    if details_href and isinstance(details_href, str):
                        details_url = urljoin(self.base_url, details_href)

                internship_id = hashlib.md5(f"{self.name}-{company}-{name}-{posted_on}".encode()).hexdigest()

                internships.append({
                    'id': internship_id,
                    'platform': self.name,
                    'name': name,
                    'company': company,
                    'stipend': stipend,
                    'type': internship_type,
                    'location': location,
                    'duration': duration,
                    'start_date': start_date,
                    'apply_by': apply_by,
                    'details_url': details_url,
                    'posted_on': posted_on
                })
            except Exception as e:
                logger.error(f"Error parsing {self.name} internship card: {e}")
                continue

        logger.info(f"✅ [{self.name}] Extracted {len(internships)} internships")
        return internships

class IntershalaScraper(InternshipScraper):
    """Internshala Scraper - Uses search endpoint approach"""
    
    def __init__(self, preferred_domains: List[str]):
        super().__init__("Internshala", preferred_domains)
        self.base_url = "https://internshala.com/internships/"
        # Note: This is a simplified approach. You may need to adjust based on Internshala's current structure
        
    def fetch_internships(self) -> List[Dict]:
        """Fetch internships from Internshala"""
        try:
            logger.info(f"🔍 [{self.name}] Fetching internship data...")
            
            # Search for internships in preferred domains
            all_internships = []
            for domain in self.preferred_domains[:3]:  # Limit API calls
                internships = self._search_domain(domain)
                all_internships.extend(internships)
                time.sleep(2)  # Rate limiting
            
            return all_internships
        except Exception as e:
            logger.error(f"❌ [{self.name}] Error fetching internships: {e}")
            return []
    
    def _search_domain(self, domain: str) -> List[Dict]:
        """Search for internships in a specific domain on Internshala"""
        try:
            # Internshala search URL structure - you may need to adjust this
            # Common search patterns for Internshala:
            search_url = f"{self.base_url}/internships/keywords-{quote(domain)}"
            # Alternative: search_url = f"{self.base_url}/internships/{quote(domain.replace(' ', '-'))}-internship"
            
            session = requests.Session()
            session.headers.update(self.headers)
            
            # Add some cookies to appear more legitimate (optional)
            session.cookies.update({
                'PHPSESSID': 'placeholder_session_id'
            })
            
            logger.info(f"🔍 [{self.name}] Searching for '{domain}' at {search_url}")
            
            response = session.get(search_url, timeout=30)
            response.raise_for_status()
            
            # Save HTML for debugging (optional)
            with open(f"internshala_{domain.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            return self._parse_internshala_html(response.text, domain)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [{self.name}] Network error searching domain {domain}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ [{self.name}] Error searching domain {domain}: {e}")
            return []
    
    def _parse_internshala_html(self, html: str, domain: str) -> List[Dict]:
        """Parse Internshala HTML using actual selectors from the website"""
        soup = BeautifulSoup(html, 'html.parser')
        internships = []
        
        # Select internship cards using the correct container class
        internship_cards = soup.select('.container-fluid.individual_internship')
        
        for card in internship_cards:
            try:
                # Extract internship name from the job title link
                name_elem = card.select_one('.job-internship-name a.job-title-href')
                name = name_elem.get_text(strip=True) if name_elem else 'N/A'
                
                # Extract company name
                company_elem = card.select_one('.company-name')
                company = company_elem.get_text(strip=True) if company_elem else 'N/A'
                
                # Extract location - look for the locations div
                location_elem = card.select_one('.locations span a')
                if not location_elem:
                    location_elem = card.select_one('.locations span')
                location = location_elem.get_text(strip=True) if location_elem else 'N/A'
                
                # Extract stipend
                stipend_elem = card.select_one('.stipend')
                stipend = stipend_elem.get_text(strip=True) if stipend_elem else 'N/A'
                
                # Extract duration - look for calendar icon parent
                duration_elem = card.select_one('.ic-16-calendar + span')
                if not duration_elem:
                    # Fallback: look for any span containing "Months" or "Month"
                    duration_spans = card.select('.row-1-item span')
                    duration_elem = next((span for span in duration_spans 
                                        if 'month' in span.get_text().lower()), None)
                duration = duration_elem.get_text(strip=True) if duration_elem else 'N/A'
                
                # Extract posting time
                posted_elem = card.select_one('.status-success span')
                posted_on = posted_elem.get_text(strip=True) if posted_elem else 'Recently'
                
                # Extract employment type (Part time, Full time, etc.)
                type_elem = card.select_one('.status-li span')
                employment_type = type_elem.get_text(strip=True) if type_elem else 'Internship'
                
                # Get internship link
                link_elem = card.select_one('a.job-title-href')
                details_url = None
                if link_elem:
                    href = link_elem.get('href')
                    if href and isinstance(href, str):
                        details_url = urljoin(self.base_url, href)
                
                # Check if actively hiring
                actively_hiring = card.select_one('.actively-hiring-badge')
                is_actively_hiring = bool(actively_hiring)
                
                # Generate unique ID
                internship_id = hashlib.md5(f"{self.name}-{company}-{name}-{posted_on}".encode()).hexdigest()
                
                internship_data = {
                    'id': internship_id,
                    'platform': self.name,
                    'name': name,
                    'company': company,
                    'stipend': stipend,
                    'type': employment_type,
                    'location': location,
                    'duration': duration,
                    'start_date': 'N/A',
                    'apply_by': 'N/A',
                    'details_url': details_url,
                    'posted_on': posted_on,
                    'actively_hiring': is_actively_hiring
                }
                
                internships.append(internship_data)
                
                logger.debug(f"✓ [{self.name}] Parsed: {name} at {company} - {stipend}")
                
            except Exception as e:
                logger.error(f"Error parsing {self.name} internship card: {e}")
                continue
        
        logger.info(f"✅ [{self.name}] Found {len(internships)} internships for domain: {domain}")
        return internships



class DualPlatformInternshipBot:
    """Enhanced bot that scrapes AICTE and Internshala platforms"""
    
    def __init__(self):
        # Configuration from environment variables
        self.config = {
            'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
            'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
            'CHECK_INTERVAL_HOURS': int(os.getenv('CHECK_INTERVAL_HOURS', '1')),
            'SEEN_FILE': 'seen_internships.json',
            'ENABLE_AICTE': os.getenv('ENABLE_AICTE', 'true').lower() == 'true',
            'ENABLE_INTERNSHALA': os.getenv('ENABLE_INTERNSHALA', 'true').lower() == 'true',
        }
        
        # Your preferred domains - customize this list
        self.preferred_domains = [
            'data science', 'machine learning', 'artificial intelligence', 'ai', 'ml',
            'data analyst', 'ai/ml'
        ]
        
        # Initialize scrapers
        self.scrapers = []
        if self.config['ENABLE_AICTE']:
            self.scrapers.append(AICTEScraper(self.preferred_domains))
        if self.config['ENABLE_INTERNSHALA']:
            self.scrapers.append(IntershalaScraper(self.preferred_domains))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate required configuration"""
        if not self.config['TELEGRAM_BOT_TOKEN']:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        if not self.config['TELEGRAM_CHAT_ID']:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is required")
        if not self.scrapers:
            raise ValueError("At least one scraper must be enabled")
    
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
            # Keep only last 2000 to prevent file from growing too large
            seen_list = list(seen_ids)[-2000:]
            with open(self.config['SEEN_FILE'], 'w') as f:
                json.dump(seen_list, f, indent=2)
            logger.debug(f"Saved {len(seen_list)} seen internship IDs")
        except Exception as e:
            logger.error(f"Could not save seen internships: {e}")
    
    def get_new_internships(self, internships: List[Dict]) -> List[Dict]:
        """Filter out previously seen internships"""
        logger.info("🆕 Checking for new internships across all platforms...")
        seen = self.load_seen_internships()
        new_internships = [i for i in internships if i['id'] not in seen]
        
        # Add new internship IDs to seen list
        for internship in new_internships:
            seen.add(internship['id'])
        
        self.save_seen_internships(seen)
        
        logger.info(f"🎉 Found {len(new_internships)} new internships total")
        return new_internships
    
    def format_telegram_message(self, internship: Dict) -> str:
        """Format internship data for Telegram message"""
        platform_emoji = {
            'AICTE': '🏛️',
            'Internshala': '💼'
        }
        
        emoji = platform_emoji.get(internship['platform'], '📋')
        
        message = f"""{emoji} *New {internship['platform']} Internship!*

📋 *Role:* {internship['name']}
🏢 *Company:* {internship['company']}
💰 *Stipend:* {internship['stipend']}
📍 *Location:* {internship['location']}
⏰ *Duration:* {internship['duration']}"""

        # Add employment type if available and different from default
        if internship.get('type', 'N/A') not in ['N/A', 'Internship']:
            message += f"\n💼 *Type:* {internship['type']}"

        if internship.get('start_date', 'N/A') != 'N/A':
            message += f"\n📅 *Start Date:* {internship['start_date']}"
        
        if internship.get('apply_by', 'N/A') != 'N/A':
            message += f"\n⚡ *Apply By:* {internship['apply_by']}"

        # Add posting time if available
        if internship.get('posted_on', 'N/A') != 'N/A':
            message += f"\n🕐 *Posted:* {internship['posted_on']}"

        # Add actively hiring badge for Internshala
        if internship.get('actively_hiring', False):
            message += f"\n🔥 *Actively Hiring!*"

        message += f"\n\n🔍 Found: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}"
        
        # Create hashtags
        company_tag = internship['company'].replace(' ', '').replace('-', '').replace('_', '').replace('.', '')[:20]  # Limit length
        message += f"\n\n#{internship['platform']}Internship #{company_tag}"
        
        return message
    
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
                'disable_web_page_preview': True
            }
            
            if apply_url:
                data['reply_markup'] = json.dumps({
                    "inline_keyboard": [
                        [{"text": f"Apply on {internship['platform']} 🚀", "url": apply_url}]
                    ]
                })
            
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"❌ Error sending Telegram message: {e}")
            return False
    
    def send_summary(self, platform_stats: Dict[str, Dict], total_new: int):
        """Send comprehensive summary report"""
        summary_lines = ["📊 *Multi-Platform Internship Bot Summary*\n"]
        
        total_found = 0
        total_filtered = 0
        
        for platform, stats in platform_stats.items():
            if stats['found'] > 0:
                emoji = {'AICTE': '🏛️', 'Internshala': '💼', 'LinkedIn': '🔗'}.get(platform, '📋')
                summary_lines.append(f"{emoji} *{platform}:*")
                summary_lines.append(f"   • Found: {stats['found']}")
                summary_lines.append(f"   • Matching: {stats['filtered']}")
                summary_lines.append(f"   • New: {stats['new']}")
                
                total_found += stats['found']
                total_filtered += stats['filtered']
        
        summary_lines.extend([
            f"\n🔍 *Total across platforms:*",
            f"   • Found: {total_found}",
            f"   • Matching your domains: {total_filtered}",
            f"   • New notifications sent: {total_new}",
            f"\n⏰ Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}",
            f"\n{'🎉 New opportunities above!' if total_new > 0 else '😴 No new internships this time'}"
        ])
        
        summary_message = "\n".join(summary_lines)
        
        try:
            url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
            data = {
                'chat_id': self.config['TELEGRAM_CHAT_ID'],
                'text': summary_message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            requests.post(url, json=data, timeout=30)
        except Exception as e:
            logger.error(f"Error sending summary: {e}")
    
    def run_check(self):
        """Main function to check for internships across AICTE and Internshala"""
        try:
            logger.info("🚀 Starting Dual-Platform Internship Bot check (AICTE + Internshala)...")
            start_time = datetime.now()
            
            all_internships = []
            platform_stats = {}
            
            # Fetch from all enabled platforms
            for scraper in self.scrapers:
                try:
                    logger.info(f"🔍 Processing {scraper.name}...")
                    
                    # Fetch raw internships
                    raw_internships = scraper.fetch_internships()
                    
                    # Filter by domain
                    filtered_internships = scraper.filter_by_domain(raw_internships)
                    all_internships.extend(filtered_internships)
                    
                    platform_stats[scraper.name] = {
                        'found': len(raw_internships),
                        'filtered': len(filtered_internships),
                        'new': 0  # Will be updated later
                    }
                    
                    # Add delay between platforms to be respectful
                    time.sleep(3)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing {scraper.name}: {e}")
                    platform_stats[scraper.name] = {'found': 0, 'filtered': 0, 'new': 0}
            
            # Get new internships
            new_internships = self.get_new_internships(all_internships)
            
            # Update platform stats with new counts
            for internship in new_internships:
                platform = internship['platform']
                if platform in platform_stats:
                    platform_stats[platform]['new'] += 1
            
            # Send notifications for new internships
            sent_count = 0
            for internship in new_internships:
                if self.send_telegram_message_with_apply(internship):
                    sent_count += 1
                    logger.info(f"📤 Sent notification: {internship['name']} at {internship['company']} ({internship['platform']})")
                    if len(new_internships) > 1:
                        time.sleep(2)
                else:
                    logger.error(f"Failed to send notification for: {internship['name']} ({internship['platform']})")
            
            # Send summary
            self.send_summary(platform_stats, sent_count)
            
            duration = datetime.now() - start_time
            logger.info(f"✅ Dual-platform check completed in {duration.total_seconds():.2f} seconds")
            logger.info(f"📊 Total: {len(all_internships)} filtered, {sent_count} new notifications sent")
            
        except Exception as e:
            logger.error(f"❌ Dual-platform bot check failed: {e}")
            # Send error notification
            try:
                error_message = f"""🚨 *Dual-Platform Bot Error*

Error: {str(e)}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}

Please check the logs for more details."""
                
                url = f"https://api.telegram.org/bot{self.config['TELEGRAM_BOT_TOKEN']}/sendMessage"
                data = {
                    'chat_id': self.config['TELEGRAM_CHAT_ID'],
                    'text': error_message,
                    'parse_mode': 'Markdown'
                }
                requests.post(url, json=data, timeout=30)
            except:
                pass
            raise
    
    def start_scheduler(self):
        """Start the scheduled job"""
        logger.info(f"🕐 Scheduling dual-platform bot to run every {self.config['CHECK_INTERVAL_HOURS']} hour(s)")
        logger.info(f"📋 Enabled platforms: {[scraper.name for scraper in self.scrapers]}")
        
        # Schedule the job
        schedule.every(self.config['CHECK_INTERVAL_HOURS']).hours.do(self.run_check)
        
        # Run once immediately
        logger.info("🏃 Running initial dual-platform check...")
        self.run_check()
        
        # Keep the scheduler running
        logger.info("⏰ Dual-platform scheduler started. Press Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(60)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("🛑 Received shutdown signal. Stopping dual-platform bot...")
    sys.exit(0)

def main():
    """Main entry point"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        bot = DualPlatformInternshipBot()
        
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
                    self.wfile.write(b'Multi-Platform Internship Bot is running!')
                    
                def log_message(self, format, *args):
                    pass
            
            httpd = socketserver.TCPServer(("", PORT), HealthCheckHandler)
            server_thread = Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()
            
            logger.info(f"🌐 Health check server started on port {PORT}")
            bot.start_scheduler()
        else:
            bot.start_scheduler()
            
    except KeyboardInterrupt:
        logger.info("👋 Multi-platform bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
