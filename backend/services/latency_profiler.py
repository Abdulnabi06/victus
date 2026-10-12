"""
Voice Latency Profiler - Measures every stage of the voice pipeline
"""
import time
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger("zyricon-backend.latency_profiler")

@dataclass
class LatencyProfile:
    """Complete latency measurements for a voice request"""
    request_id: str
    timestamp: str
    
    # Frontend timing (in ms)
    audio_capture_ms: float = 0.0
    audio_encoding_ms: float = 0.0
    
    # Backend timing (in ms)
    request_receive_ms: float = 0.0
    api_send_ms: float = 0.0
    api_first_token_ms: float = 0.0  # Time to first audio chunk from NVIDIA
    api_total_ms: float = 0.0
    response_stream_ms: float = 0.0
    
    # Total end-to-end (in ms)
    total_user_perceivable_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_log_string(self) -> str:
        """Format for console logging"""
        return (
            f"VOICE_METRICS[{self.request_id[:8]}] "
            f"capture={self.audio_capture_ms:.0f}ms "
            f"encode={self.audio_encoding_ms:.0f}ms "
            f"recv={self.request_receive_ms:.0f}ms "
            f"send={self.api_send_ms:.0f}ms "
            f"first_token={self.api_first_token_ms:.0f}ms "
            f"stream={self.response_stream_ms:.0f}ms "
            f"total={self.total_user_perceivable_ms:.0f}ms"
        )


class LatencyProfiler:
    """Track and log latency for voice requests"""
    
    def __init__(self):
        self.profiles: Dict[str, LatencyProfile] = {}
        self.stage_timings: Dict[str, Dict[str, float]] = {}
    
    def create_profile(self, request_id: str) -> LatencyProfile:
        """Create a new latency profile"""
        profile = LatencyProfile(
            request_id=request_id,
            timestamp=datetime.now().isoformat()
        )
        self.profiles[request_id] = profile
        self.stage_timings[request_id] = {}
        return profile
    
    def mark_stage(self, request_id: str, stage: str, elapsed_ms: float):
        """Mark completion of a processing stage"""
        if request_id not in self.stage_timings:
            self.stage_timings[request_id] = {}
        
        self.stage_timings[request_id][stage] = elapsed_ms
        logger.debug(f"[{request_id[:8]}] {stage}: {elapsed_ms:.0f}ms")
    
    def set_metric(self, request_id: str, metric_name: str, value_ms: float):
        """Set a specific latency metric"""
        if request_id in self.profiles:
            setattr(self.profiles[request_id], metric_name, value_ms)
    
    def finalize(self, request_id: str):
        """Calculate total latency and log results"""
        if request_id not in self.profiles:
            return
        
        profile = self.profiles[request_id]
        
        # Calculate total user-perceivable latency
        profile.total_user_perceivable_ms = (
            profile.audio_capture_ms +
            profile.audio_encoding_ms +
            profile.request_receive_ms +
            profile.api_send_ms +
            profile.api_first_token_ms
        )
        
        logger.info(profile.to_log_string())
        return profile
    
    def get_profile(self, request_id: str) -> Optional[LatencyProfile]:
        """Retrieve a completed profile"""
        return self.profiles.get(request_id)
    
    def get_stats(self) -> Dict:
        """Return aggregate statistics"""
        if not self.profiles:
            return {"status": "no_data"}
        
        profiles = list(self.profiles.values())
        totals = [p.total_user_perceivable_ms for p in profiles if p.total_user_perceivable_ms > 0]
        
        if not totals:
            return {"status": "no_completed_requests"}
        
        totals.sort()
        return {
            "requests_completed": len(totals),
            "average_ms": sum(totals) / len(totals),
            "median_ms": totals[len(totals) // 2],
            "p95_ms": totals[int(len(totals) * 0.95)],
            "p99_ms": totals[int(len(totals) * 0.99)],
            "min_ms": min(totals),
            "max_ms": max(totals),
        }


# Global profiler instance
latency_profiler = LatencyProfiler()
