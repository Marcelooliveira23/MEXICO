"""
Performance Monitor for Aircraft Inspection Analysis
Tracks application metrics, response times, and resource usage
"""

import time
import psutil
import json
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class PerformanceMetric:
    """Performance metric data"""
    timestamp: str
    operation: str
    duration_ms: float
    memory_mb: float
    cpu_percent: float
    success: bool
    error: str = ""


class PerformanceMonitor:
    """Monitor and log application performance"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.metrics: List[PerformanceMetric] = []
        self.process = psutil.Process()
    
    def measure(self, operation_name: str):
        """Decorator to measure function performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Get initial metrics
                start_time = time.time()
                start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                cpu_start = self.process.cpu_percent()
                
                success = True
                error_msg = ""
                result = None
                
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    success = False
                    error_msg = str(e)
                    raise
                finally:
                    # Calculate metrics
                    duration = (time.time() - start_time) * 1000  # ms
                    end_memory = self.process.memory_info().rss / 1024 / 1024
                    cpu_percent = self.process.cpu_percent()
                    
                    # Record metric
                    metric = PerformanceMetric(
                        timestamp=datetime.now().isoformat(),
                        operation=operation_name,
                        duration_ms=round(duration, 2),
                        memory_mb=round(end_memory - start_memory, 2),
                        cpu_percent=round(cpu_percent - cpu_start, 2),
                        success=success,
                        error=error_msg
                    )
                    
                    self.metrics.append(metric)
                    
                    # Log slow operations
                    if duration > 1000:  # > 1 second
                        print(f"⚠️  SLOW OPERATION: {operation_name} took {duration:.0f}ms")
                
                return result
            
            return wrapper
        return decorator
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate performance statistics"""
        if not self.metrics:
            return {}
        
        operations = {}
        for metric in self.metrics:
            if metric.operation not in operations:
                operations[metric.operation] = []
            operations[metric.operation].append(metric.duration_ms)
        
        stats = {}
        for op, durations in operations.items():
            stats[op] = {
                'count': len(durations),
                'avg_ms': round(sum(durations) / len(durations), 2),
                'min_ms': round(min(durations), 2),
                'max_ms': round(max(durations), 2),
                'total_ms': round(sum(durations), 2)
            }
        
        return stats
    
    def save_report(self):
        """Save performance report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.log_dir / f"performance_{timestamp}.json"
        
        report = {
            'generated': datetime.now().isoformat(),
            'total_metrics': len(self.metrics),
            'statistics': self.get_statistics(),
            'metrics': [asdict(m) for m in self.metrics[-100:]]  # Last 100 metrics
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Performance report saved: {report_file}")
        return report_file
    
    def print_summary(self):
        """Print performance summary to console"""
        print("\n" + "=" * 70)
        print("PERFORMANCE SUMMARY")
        print("=" * 70)
        
        stats = self.get_statistics()
        
        if not stats:
            print("No performance data available")
            return
        
        print(f"\nTotal Operations: {len(self.metrics)}")
        print(f"Unique Operation Types: {len(stats)}")
        
        # Failed operations
        failed = [m for m in self.metrics if not m.success]
        if failed:
            print(f"\n⚠️  Failed Operations: {len(failed)}")
            for metric in failed[-5:]:  # Last 5 failures
                print(f"   - {metric.operation}: {metric.error}")
        
        print("\nOperation Statistics:")
        print(f"{'Operation':<30} {'Count':>8} {'Avg (ms)':>12} {'Max (ms)':>12}")
        print("-" * 70)
        
        for op, data in sorted(stats.items(), key=lambda x: x[1]['avg_ms'], reverse=True):
            print(f"{op:<30} {data['count']:>8} {data['avg_ms']:>12.2f} {data['max_ms']:>12.2f}")
        
        print("=" * 70)
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get current system resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': {
                'total_mb': round(psutil.virtual_memory().total / 1024 / 1024, 2),
                'available_mb': round(psutil.virtual_memory().available / 1024 / 1024, 2),
                'used_percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total_gb': round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2),
                'free_gb': round(psutil.disk_usage('/').free / 1024 / 1024 / 1024, 2),
                'used_percent': psutil.disk_usage('/').percent
            },
            'process': {
                'memory_mb': round(self.process.memory_info().rss / 1024 / 1024, 2),
                'cpu_percent': self.process.cpu_percent()
            }
        }
    
    def check_resource_health(self) -> Dict[str, str]:
        """Check if system resources are healthy"""
        info = self.get_system_info()
        health = {}
        
        # Memory check
        if info['memory']['used_percent'] > 90:
            health['memory'] = "CRITICAL - Memory usage > 90%"
        elif info['memory']['used_percent'] > 75:
            health['memory'] = "WARNING - Memory usage > 75%"
        else:
            health['memory'] = "OK"
        
        # CPU check
        if info['cpu_percent'] > 90:
            health['cpu'] = "CRITICAL - CPU usage > 90%"
        elif info['cpu_percent'] > 75:
            health['cpu'] = "WARNING - CPU usage > 75%"
        else:
            health['cpu'] = "OK"
        
        # Disk check
        if info['disk']['used_percent'] > 95:
            health['disk'] = "CRITICAL - Disk usage > 95%"
        elif info['disk']['used_percent'] > 85:
            health['disk'] = "WARNING - Disk usage > 85%"
        else:
            health['disk'] = "OK"
        
        return health


# Global performance monitor instance
_monitor = None


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def measure_performance(operation_name: str):
    """Convenience decorator for performance measurement"""
    monitor = get_monitor()
    return monitor.measure(operation_name)


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    print("=" * 70)
    print("PERFORMANCE MONITORING SYSTEM TEST")
    print("=" * 70)
    
    monitor = PerformanceMonitor()
    
    # Test 1: Fast operation
    @monitor.measure("fast_operation")
    def fast_task():
        time.sleep(0.1)
        return "Done"
    
    # Test 2: Slow operation
    @monitor.measure("slow_operation")
    def slow_task():
        time.sleep(2.0)
        return "Done"
    
    # Test 3: Memory intensive
    @monitor.measure("memory_operation")
    def memory_task():
        data = [i for i in range(1000000)]
        return len(data)
    
    # Run tests
    print("\nRunning performance tests...")
    fast_task()
    fast_task()
    fast_task()
    
    slow_task()
    
    memory_task()
    
    # Show results
    monitor.print_summary()
    
    # Show system info
    print("\n" + "=" * 70)
    print("SYSTEM RESOURCE USAGE")
    print("=" * 70)
    info = monitor.get_system_info()
    print(f"\nCPU Usage: {info['cpu_percent']}%")
    print(f"Memory: {info['memory']['used_percent']}% ({info['memory']['available_mb']:.0f} MB available)")
    print(f"Disk: {info['disk']['used_percent']}% ({info['disk']['free_gb']:.1f} GB free)")
    print(f"Process Memory: {info['process']['memory_mb']:.2f} MB")
    
    # Health check
    print("\n" + "=" * 70)
    print("RESOURCE HEALTH CHECK")
    print("=" * 70)
    health = monitor.check_resource_health()
    for resource, status in health.items():
        icon = "✅" if status == "OK" else "⚠️" if "WARNING" in status else "❌"
        print(f"{icon} {resource.upper()}: {status}")
    
    # Save report
    print("\n" + "=" * 70)
    monitor.save_report()
    print("=" * 70)
