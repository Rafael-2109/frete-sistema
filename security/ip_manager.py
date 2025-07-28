"""
IP Manager for Security System
Handles IP whitelisting, blacklisting, and reputation tracking
"""

import asyncio
import ipaddress
from typing import Dict, Set, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json
import logging
import aiofiles
from enum import Enum
import geoip2.database
import aiohttp

logger = logging.getLogger(__name__)


class IPReputation(Enum):
    """IP reputation levels"""
    TRUSTED = 5
    GOOD = 4
    NEUTRAL = 3
    SUSPICIOUS = 2
    MALICIOUS = 1


class IPRecord:
    """Record for tracking IP behavior"""
    
    def __init__(self, ip: str):
        self.ip = ip
        self.first_seen = datetime.now()
        self.last_seen = datetime.now()
        self.request_count = 0
        self.blocked_count = 0
        self.violation_count = 0
        self.reputation_score = 50  # 0-100 scale
        self.tags = set()
        self.notes = []
        self.country = None
        self.asn = None
        self.is_proxy = False
        self.is_hosting = False
    
    def update_activity(self):
        """Update last seen timestamp"""
        self.last_seen = datetime.now()
        self.request_count += 1
    
    def record_violation(self, violation_type: str, severity: int = 1):
        """Record a security violation"""
        self.violation_count += 1
        self.reputation_score = max(0, self.reputation_score - (severity * 5))
        self.notes.append({
            "timestamp": datetime.now().isoformat(),
            "type": violation_type,
            "severity": severity
        })
    
    def record_block(self):
        """Record that IP was blocked"""
        self.blocked_count += 1
        self.reputation_score = max(0, self.reputation_score - 10)
    
    def improve_reputation(self, amount: int = 1):
        """Improve reputation for good behavior"""
        self.reputation_score = min(100, self.reputation_score + amount)
    
    def get_reputation_level(self) -> IPReputation:
        """Get reputation level based on score"""
        if self.reputation_score >= 80:
            return IPReputation.TRUSTED
        elif self.reputation_score >= 60:
            return IPReputation.GOOD
        elif self.reputation_score >= 40:
            return IPReputation.NEUTRAL
        elif self.reputation_score >= 20:
            return IPReputation.SUSPICIOUS
        else:
            return IPReputation.MALICIOUS
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "ip": self.ip,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "request_count": self.request_count,
            "blocked_count": self.blocked_count,
            "violation_count": self.violation_count,
            "reputation_score": self.reputation_score,
            "tags": list(self.tags),
            "notes": self.notes,
            "country": self.country,
            "asn": self.asn,
            "is_proxy": self.is_proxy,
            "is_hosting": self.is_hosting
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'IPRecord':
        """Create from dictionary"""
        record = cls(data["ip"])
        record.first_seen = datetime.fromisoformat(data["first_seen"])
        record.last_seen = datetime.fromisoformat(data["last_seen"])
        record.request_count = data["request_count"]
        record.blocked_count = data["blocked_count"]
        record.violation_count = data["violation_count"]
        record.reputation_score = data["reputation_score"]
        record.tags = set(data.get("tags", []))
        record.notes = data.get("notes", [])
        record.country = data.get("country")
        record.asn = data.get("asn")
        record.is_proxy = data.get("is_proxy", False)
        record.is_hosting = data.get("is_hosting", False)
        return record


class IPManager:
    """Manages IP whitelists, blacklists, and reputation"""
    
    def __init__(self, geoip_db_path: Optional[str] = None):
        # Lists
        self.whitelist: Set[str] = set()
        self.blacklist: Set[str] = set()
        self.graylist: Set[str] = set()
        
        # IP records
        self.ip_records: Dict[str, IPRecord] = {}
        
        # Subnet lists
        self.whitelist_subnets: List[ipaddress.IPv4Network] = []
        self.blacklist_subnets: List[ipaddress.IPv4Network] = []
        
        # Temporary blocks
        self.temp_blocks: Dict[str, datetime] = {}
        
        # Configuration
        self.config = {
            "auto_blacklist_threshold": 10,  # Reputation score
            "auto_graylist_threshold": 30,  # Reputation score
            "temp_block_duration": 3600,     # 1 hour
            "reputation_decay_rate": 0.95,   # Daily decay
            "max_records": 100000,           # Max IP records to keep
        }
        
        # GeoIP database
        self.geoip_reader = None
        if geoip_db_path:
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
            except Exception as e:
                logger.error(f"Failed to load GeoIP database: {e}")
        
        # Known bad IP sources
        self.threat_feeds = [
            "https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt",
            "https://www.spamhaus.org/drop/drop.txt",
        ]
        
        # Statistics
        self.stats = defaultdict(int)
        
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize IP manager"""
        # Load saved data
        await self._load_data()
        
        # Load threat intelligence feeds
        asyncio.create_task(self._update_threat_feeds())
        
        # Start maintenance tasks
        asyncio.create_task(self._maintenance_task())
        
        logger.info(f"IP Manager initialized with {len(self.whitelist)} whitelisted, "
                   f"{len(self.blacklist)} blacklisted IPs")
    
    async def _load_data(self):
        """Load saved IP data"""
        try:
            async with aiofiles.open("security/ip_data.json", "r") as f:
                data = json.loads(await f.read())
                
                self.whitelist = set(data.get("whitelist", []))
                self.blacklist = set(data.get("blacklist", []))
                self.graylist = set(data.get("graylist", []))
                
                # Load subnets
                for subnet in data.get("whitelist_subnets", []):
                    self.whitelist_subnets.append(ipaddress.IPv4Network(subnet))
                
                for subnet in data.get("blacklist_subnets", []):
                    self.blacklist_subnets.append(ipaddress.IPv4Network(subnet))
                
                # Load IP records
                for ip, record_data in data.get("ip_records", {}).items():
                    self.ip_records[ip] = IPRecord.from_dict(record_data)
                
                logger.info("Loaded IP data from disk")
        except FileNotFoundError:
            logger.info("No saved IP data found")
        except Exception as e:
            logger.error(f"Error loading IP data: {e}")
    
    async def _save_data(self):
        """Save IP data"""
        try:
            data = {
                "whitelist": list(self.whitelist),
                "blacklist": list(self.blacklist),
                "graylist": list(self.graylist),
                "whitelist_subnets": [str(net) for net in self.whitelist_subnets],
                "blacklist_subnets": [str(net) for net in self.blacklist_subnets],
                "ip_records": {
                    ip: record.to_dict() 
                    for ip, record in list(self.ip_records.items())[:self.config["max_records"]]
                }
            }
            
            async with aiofiles.open("security/ip_data.json", "w") as f:
                await f.write(json.dumps(data, indent=2))
                
            logger.info("Saved IP data to disk")
        except Exception as e:
            logger.error(f"Error saving IP data: {e}")
    
    async def check_ip(self, ip: str) -> Tuple[bool, Optional[str]]:
        """Check if IP is allowed"""
        # Check permanent blacklist
        if await self.is_blacklisted(ip):
            self.stats["blacklisted_blocks"] += 1
            return False, "IP is blacklisted"
        
        # Check whitelist
        if await self.is_whitelisted(ip):
            return True, None
        
        # Check temporary blocks
        if ip in self.temp_blocks:
            if self.temp_blocks[ip] > datetime.now():
                self.stats["temp_blocks"] += 1
                return False, "IP is temporarily blocked"
            else:
                async with self._lock:
                    del self.temp_blocks[ip]
        
        # Check graylist
        if ip in self.graylist:
            self.stats["graylist_checks"] += 1
            # Additional verification might be required
            return True, "graylist"
        
        # Get or create IP record
        record = await self.get_or_create_record(ip)
        
        # Check reputation
        reputation = record.get_reputation_level()
        if reputation == IPReputation.MALICIOUS:
            await self.add_to_blacklist(ip, "Low reputation score")
            return False, "IP has malicious reputation"
        elif reputation == IPReputation.SUSPICIOUS:
            await self.add_to_graylist(ip)
            return True, "graylist"
        
        return True, None
    
    async def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted"""
        if ip in self.whitelist:
            return True
        
        # Check subnet whitelists
        try:
            ip_obj = ipaddress.IPv4Address(ip)
            for subnet in self.whitelist_subnets:
                if ip_obj in subnet:
                    return True
        except:
            pass
        
        return False
    
    async def is_blacklisted(self, ip: str) -> bool:
        """Check if IP is blacklisted"""
        if ip in self.blacklist:
            return True
        
        # Check subnet blacklists
        try:
            ip_obj = ipaddress.IPv4Address(ip)
            for subnet in self.blacklist_subnets:
                if ip_obj in subnet:
                    return True
        except:
            pass
        
        return False
    
    async def add_to_whitelist(self, ip: str, reason: str = ""):
        """Add IP to whitelist"""
        async with self._lock:
            self.whitelist.add(ip)
            self.blacklist.discard(ip)
            self.graylist.discard(ip)
            
            # Update record
            record = await self.get_or_create_record(ip)
            record.tags.add("whitelisted")
            record.reputation_score = 100
            record.notes.append({
                "timestamp": datetime.now().isoformat(),
                "action": "whitelisted",
                "reason": reason
            })
            
            await self._save_data()
            logger.info(f"Added {ip} to whitelist: {reason}")
    
    async def add_to_blacklist(self, ip: str, reason: str = ""):
        """Add IP to blacklist"""
        async with self._lock:
            self.blacklist.add(ip)
            self.whitelist.discard(ip)
            self.graylist.discard(ip)
            
            # Update record
            record = await self.get_or_create_record(ip)
            record.tags.add("blacklisted")
            record.reputation_score = 0
            record.notes.append({
                "timestamp": datetime.now().isoformat(),
                "action": "blacklisted",
                "reason": reason
            })
            
            await self._save_data()
            logger.warning(f"Added {ip} to blacklist: {reason}")
    
    async def add_to_graylist(self, ip: str):
        """Add IP to graylist for additional monitoring"""
        async with self._lock:
            self.graylist.add(ip)
            
            # Update record
            record = await self.get_or_create_record(ip)
            record.tags.add("graylisted")
            
            logger.info(f"Added {ip} to graylist")
    
    async def add_subnet_whitelist(self, subnet: str):
        """Add subnet to whitelist"""
        try:
            network = ipaddress.IPv4Network(subnet)
            async with self._lock:
                self.whitelist_subnets.append(network)
                await self._save_data()
            logger.info(f"Added subnet {subnet} to whitelist")
        except Exception as e:
            logger.error(f"Invalid subnet {subnet}: {e}")
    
    async def add_subnet_blacklist(self, subnet: str):
        """Add subnet to blacklist"""
        try:
            network = ipaddress.IPv4Network(subnet)
            async with self._lock:
                self.blacklist_subnets.append(network)
                await self._save_data()
            logger.info(f"Added subnet {subnet} to blacklist")
        except Exception as e:
            logger.error(f"Invalid subnet {subnet}: {e}")
    
    async def temporary_block(self, ip: str, duration: int = None):
        """Temporarily block an IP"""
        if duration is None:
            duration = self.config["temp_block_duration"]
        
        async with self._lock:
            self.temp_blocks[ip] = datetime.now() + timedelta(seconds=duration)
            
            # Update record
            record = await self.get_or_create_record(ip)
            record.record_block()
            
        logger.info(f"Temporarily blocked {ip} for {duration} seconds")
    
    async def get_or_create_record(self, ip: str) -> IPRecord:
        """Get or create IP record"""
        if ip not in self.ip_records:
            record = IPRecord(ip)
            
            # Enrich with GeoIP data
            if self.geoip_reader:
                try:
                    response = self.geoip_reader.city(ip)
                    record.country = response.country.iso_code
                    record.asn = response.traits.autonomous_system_number
                except:
                    pass
            
            self.ip_records[ip] = record
        
        return self.ip_records[ip]
    
    async def record_violation(self, ip: str, violation_type: str, severity: int = 1):
        """Record a security violation for an IP"""
        record = await self.get_or_create_record(ip)
        record.record_violation(violation_type, severity)
        
        # Auto-blacklist if reputation too low
        if record.reputation_score <= self.config["auto_blacklist_threshold"]:
            await self.add_to_blacklist(ip, "Auto-blacklisted due to low reputation")
        elif record.reputation_score <= self.config["auto_graylist_threshold"]:
            await self.add_to_graylist(ip)
        
        self.stats[f"violation_{violation_type}"] += 1
    
    async def record_good_behavior(self, ip: str):
        """Record good behavior for an IP"""
        record = await self.get_or_create_record(ip)
        record.improve_reputation()
        record.update_activity()
    
    async def _update_threat_feeds(self):
        """Update threat intelligence feeds"""
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    for feed_url in self.threat_feeds:
                        try:
                            async with session.get(feed_url, timeout=30) as response:
                                if response.status == 200:
                                    content = await response.text()
                                    await self._process_threat_feed(content)
                        except Exception as e:
                            logger.error(f"Error fetching threat feed {feed_url}: {e}")
                
                logger.info("Updated threat intelligence feeds")
                await asyncio.sleep(3600)  # Update hourly
            except Exception as e:
                logger.error(f"Error updating threat feeds: {e}")
                await asyncio.sleep(3600)
    
    async def _process_threat_feed(self, content: str):
        """Process threat feed content"""
        new_threats = 0
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Extract IP or subnet
                parts = line.split()
                if parts:
                    ip_or_subnet = parts[0]
                    if "/" in ip_or_subnet:
                        # It's a subnet
                        if ip_or_subnet not in [str(net) for net in self.blacklist_subnets]:
                            await self.add_subnet_blacklist(ip_or_subnet)
                            new_threats += 1
                    else:
                        # It's an IP
                        if ip_or_subnet not in self.blacklist:
                            await self.add_to_blacklist(ip_or_subnet, "Threat intelligence feed")
                            new_threats += 1
        
        if new_threats > 0:
            logger.info(f"Added {new_threats} IPs/subnets from threat feed")
    
    async def _maintenance_task(self):
        """Periodic maintenance tasks"""
        while True:
            try:
                async with self._lock:
                    # Clean expired temporary blocks
                    expired = [ip for ip, exp_time in self.temp_blocks.items()
                             if exp_time < datetime.now()]
                    for ip in expired:
                        del self.temp_blocks[ip]
                    
                    # Apply reputation decay
                    for record in self.ip_records.values():
                        # Only decay reputation for IPs not seen recently
                        if record.last_seen < datetime.now() - timedelta(days=1):
                            record.reputation_score *= self.config["reputation_decay_rate"]
                    
                    # Remove old records if over limit
                    if len(self.ip_records) > self.config["max_records"]:
                        # Sort by last seen and remove oldest
                        sorted_ips = sorted(
                            self.ip_records.items(),
                            key=lambda x: x[1].last_seen
                        )
                        to_remove = len(self.ip_records) - self.config["max_records"]
                        for ip, _ in sorted_ips[:to_remove]:
                            del self.ip_records[ip]
                
                # Save data periodically
                await self._save_data()
                
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Error in maintenance task: {e}")
                await asyncio.sleep(300)
    
    def get_statistics(self) -> dict:
        """Get IP manager statistics"""
        return {
            "whitelisted_ips": len(self.whitelist),
            "blacklisted_ips": len(self.blacklist),
            "graylisted_ips": len(self.graylist),
            "whitelisted_subnets": len(self.whitelist_subnets),
            "blacklisted_subnets": len(self.blacklist_subnets),
            "tracked_ips": len(self.ip_records),
            "temp_blocks": len(self.temp_blocks),
            **self.stats
        }
    
    async def get_ip_info(self, ip: str) -> dict:
        """Get detailed information about an IP"""
        record = self.ip_records.get(ip)
        if not record:
            return {"ip": ip, "status": "unknown"}
        
        return {
            **record.to_dict(),
            "reputation_level": record.get_reputation_level().name,
            "is_whitelisted": await self.is_whitelisted(ip),
            "is_blacklisted": await self.is_blacklisted(ip),
            "is_graylisted": ip in self.graylist,
            "is_temp_blocked": ip in self.temp_blocks
        }


# Create global IP manager instance
ip_manager = IPManager()