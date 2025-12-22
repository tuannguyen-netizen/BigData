"""
Celery Worker - FIXED VERSION
Sửa các lỗi:
1. Backend URL syntax
2. Thêm health check tasks
3. Better error handling
"""
from celery import Celery
import subprocess
import os
import socket
import time

# ✅ FIX: Đúng cú pháp env var với default value
broker_url = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@master:5672//')
backend_url = os.environ.get('CELERY_RESULT_BACKEND', 'db+postgresql://airflow:airflow@master/airflow')

app = Celery(
    'system_worker',
    broker=broker_url,
    backend=backend_url
)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=True,
    task_routes={
        'mycelery.system_worker.*': {'queue': 'system'},
    },
)

QUEUE_MAPPING = {
    'spark': 'spark',
    'kafka': 'node_57',
    'hadoop': 'node_57',
}


@app.task(bind=True)
def run_command(self, command, env_vars=None):
    """Chạy một lệnh shell"""
    try:
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            env=env
        )
        return {
            'status': 'success',
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'status': 'error',
            'message': 'Command execution timed out (300s)'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


# ✅ NEW: Health check task cho Kafka
@app.task(bind=True)
def check_kafka_health(self, broker_host='localhost', broker_port=9092, timeout=5):
    """Kiểm tra Kafka broker có đang chạy không"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((broker_host, broker_port))
        sock.close()
        
        if result == 0:
            return {
                'status': 'success',
                'healthy': True,
                'message': f'Kafka broker at {broker_host}:{broker_port} is healthy'
            }
        else:
            return {
                'status': 'success',
                'healthy': False,
                'message': f'Kafka broker at {broker_host}:{broker_port} is not responding'
            }
    except Exception as e:
        return {
            'status': 'error',
            'healthy': False,
            'message': str(e)
        }


# ✅ NEW: Health check task cho Spark
@app.task(bind=True)
def check_spark_health(self, master_host='localhost', master_port=7077, web_ui_port=8080, timeout=5):
    """Check if Spark Master is running and responsive."""
    import urllib.request
    import urllib.error
    
    health_status = {
        'status': 'success',
        'healthy': False,
        'rpc_port_open': False,
        'web_ui_accessible': False,
        'message': '',
        'details': {}
    }
    
    # 1. Check RPC port (7077) - Spark Master RPC endpoint
    try:
        with socket.create_connection((master_host, master_port), timeout=timeout):
            health_status['rpc_port_open'] = True
            health_status['message'] = f'Spark Master RPC port {master_port} is open'
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        health_status['message'] = f'Spark Master RPC port {master_port} is not accessible: {str(e)}'
        return health_status
    except Exception as e:
        health_status['status'] = 'error'
        health_status['message'] = f'Error checking RPC port: {str(e)}'
        return health_status
    
    # 2. Check Web UI port (8080) - Spark Master Web UI
    try:
        web_ui_url = f'http://{master_host}:{web_ui_port}'
        req = urllib.request.Request(web_ui_url, method='GET')
        req.add_header('User-Agent', 'SparkHealthCheck/1.0')
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                health_status['web_ui_accessible'] = True
                # Try to parse HTML to get cluster info
                try:
                    html_content = response.read().decode('utf-8', errors='ignore')
                    # Extract worker count if available
                    if 'Workers' in html_content:
                        import re
                        worker_match = re.search(r'Workers:\s*(\d+)', html_content)
                        if worker_match:
                            health_status['details']['num_workers'] = int(worker_match.group(1))
                except Exception:
                    pass
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as e:
        # Web UI không accessible nhưng RPC port OK thì vẫn có thể healthy
        health_status['details']['web_ui_error'] = f'Web UI not accessible: {str(e)}'
    except Exception as e:
        health_status['details']['web_ui_error'] = f'Error checking Web UI: {str(e)}'
    
    # 3. Check Spark Master bằng spark-submit (nếu có)
    try:
        spark_submit_check = subprocess.run(
            ['spark-submit', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if spark_submit_check.returncode == 0:
            health_status['details']['spark_version'] = spark_submit_check.stdout.split('\n')[0] if spark_submit_check.stdout else 'unknown'
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    except Exception:
        pass
    
    # 4. Kết luận: Healthy nếu RPC port mở (đây là điều kiện quan trọng nhất)
    if health_status['rpc_port_open']:
        health_status['healthy'] = True
        if not health_status['message']:
            health_status['message'] = f'Spark Master at {master_host}:{master_port} is healthy'
        if health_status['web_ui_accessible']:
            health_status['message'] += f' (Web UI accessible at port {web_ui_port})'
        else:
            health_status['message'] += f' (Web UI may not be accessible)'
    else:
        health_status['healthy'] = False
    
    return health_status


# ✅ NEW: Health check task cho HDFS
@app.task(bind=True)
def check_hdfs_health(self, namenode_host='localhost', namenode_port=8020, timeout=5):
    """Kiểm tra HDFS Namenode có đang chạy không"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((namenode_host, namenode_port))
        sock.close()
        
        if result == 0:
            # Kiểm tra thêm bằng hdfs dfsadmin -report
            hdfs_check = subprocess.run(
                ['hdfs', 'dfsadmin', '-report'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if hdfs_check.returncode == 0 and 'Live datanodes' in hdfs_check.stdout:
                return {
                    'status': 'success',
                    'healthy': True,
                    'message': f'HDFS Namenode at {namenode_host}:{namenode_port} is healthy'
                }
            else:
                return {
                    'status': 'success',
                    'healthy': False,
                    'message': 'HDFS Namenode port open but cluster unhealthy'
                }
        else:
            return {
                'status': 'success',
                'healthy': False,
                'message': f'HDFS Namenode at {namenode_host}:{namenode_port} is not responding'
            }
    except Exception as e:
        return {
            'status': 'error',
            'healthy': False,
            'message': str(e)
        }


# ✅ NEW: Verify HDFS file exists
@app.task(bind=True)
def verify_hdfs_file(self, hdfs_path, min_size_bytes=0):
    """Kiểm tra file/directory có tồn tại trên HDFS không"""
    try:
        # Check if path exists
        check_cmd = f"hdfs dfs -test -e {hdfs_path}"
        result = subprocess.run(
            check_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                'status': 'success',
                'exists': False,
                'message': f'Path {hdfs_path} does not exist on HDFS'
            }
        
        # Get file size
        stat_cmd = f"hdfs dfs -du -s {hdfs_path}"
        stat_result = subprocess.run(
            stat_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if stat_result.returncode == 0:
            size_bytes = int(stat_result.stdout.split()[0])
            return {
                'status': 'success',
                'exists': True,
                'size_bytes': size_bytes,
                'size_mb': round(size_bytes / 1024 / 1024, 2),
                'meets_min_size': size_bytes >= min_size_bytes,
                'message': f'Path {hdfs_path} exists ({size_bytes} bytes)'
            }
        else:
            return {
                'status': 'success',
                'exists': True,
                'message': f'Path {hdfs_path} exists but cannot get size'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@app.task(bind=True)
def docker_run(self, image, container_name=None, ports=None, volumes=None, env_vars=None, detach=True):
    """Chạy Docker container"""
    try:
        cmd = ['docker', 'run']

        if detach:
            cmd.append('-d')

        if container_name:
            cmd.extend(['--name', container_name])

        if ports:
            for port in ports:
                cmd.extend(['-p', port])

        if volumes:
            for volume in volumes:
                cmd.extend(['-v', volume])

        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(['-e', f'{key}={value}'])

        cmd.append(image)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        return {
            'status': 'success',
            'container_id': result.stdout.strip(),
            'stderr': result.stderr,
            'return_code': result.returncode
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@app.task(bind=True)
def docker_stop(self, container_name):
    """Dừng Docker container"""
    try:
        result = subprocess.run(
            ['docker', 'stop', container_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            'status': 'success',
            'message': f'Container {container_name} stopped',
            'return_code': result.returncode
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@app.task(bind=True)
def docker_remove(self, container_name):
    """Xóa Docker container"""
    try:
        result = subprocess.run(
            ['docker', 'rm', container_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            'status': 'success',
            'message': f'Container {container_name} removed',
            'return_code': result.returncode
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@app.task(bind=True)
def docker_ps(self, all_containers=False):
    """Liệt kê Docker containers"""
    try:
        cmd = ['docker', 'ps']
        if all_containers:
            cmd.append('-a')

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            'status': 'success',
            'output': result.stdout,
            'return_code': result.returncode
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


@app.task(bind=True)
def docker_compose_up(self, path, services=None, detach=True, build=False, force_recreate=False):
    """Chạy docker-compose up với path được chỉ định"""
    path = os.path.expanduser(path)
    
    # Cleanup trước
    try:
        down_cmd = ['docker', 'compose', '-f', path, 'down', '--remove-orphans']
        subprocess.run(down_cmd, capture_output=True, text=True, timeout=120)
    except Exception:
        pass
    
    cmd = ['docker', 'compose', '-f', path, 'up']

    if detach:
        cmd.append('-d')
    if build:
        cmd.append('--build')
    if force_recreate:
        cmd.append('--force-recreate')

    if services:
        if isinstance(services, str):
            cmd.append(services)
        elif isinstance(services, list):
            cmd.extend(services)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise Exception('Docker compose up timed out (600s)')

    if result.returncode != 0:
        if 'already in use' in result.stderr or 'Conflict' in result.stderr:
            # Retry logic
            import re
            container_names = re.findall(r'container name "([^"]+)"', result.stderr)
            for container_name in container_names:
                try:
                    subprocess.run(['docker', 'rm', '-f', container_name], 
                                 capture_output=True, text=True, timeout=30)
                except Exception:
                    pass
            
            try:
                subprocess.run(['docker', 'compose', '-f', path, 'down', '--remove-orphans'],
                             capture_output=True, text=True, timeout=120)
            except Exception:
                pass
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode != 0:
                raise Exception(f"Docker compose up failed after retry: {result.stderr}")
        else:
            raise Exception(f"Docker compose up failed: {result.stderr}")

    return {
        'status': 'success',
        'stdout': result.stdout,
        'stderr': result.stderr,
        'return_code': result.returncode
    }


@app.task(bind=True)
def docker_compose_down(self, path, services=None, volumes=False, remove_orphans=False):
    """Dừng và xóa containers với docker-compose down"""
    path = os.path.expanduser(path)

    try:
        if services:
            if isinstance(services, str):
                services = [services]

            stop_cmd = ['docker', 'compose', '-f', path, 'stop'] + services
            subprocess.run(stop_cmd, capture_output=True, text=True, timeout=120)

            rm_cmd = ['docker', 'compose', '-f', path, 'rm', '-f'] + services
            if volumes:
                rm_cmd.insert(5, '-v')
            result = subprocess.run(rm_cmd, capture_output=True, text=True, timeout=120)
        else:
            cmd = ['docker', 'compose', '-f', path, 'down']
            if volumes:
                cmd.append('-v')
            if remove_orphans:
                cmd.append('--remove-orphans')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise Exception('Docker compose down timed out (300s)')

    if result.returncode != 0:
        raise Exception(f"Docker compose down failed: {result.stderr}")

    return {
        'status': 'success',
        'stdout': result.stdout,
        'stderr': result.stderr,
        'return_code': result.returncode
    }


@app.task(bind=True)
def docker_compose_ps(self, path):
    """Liệt kê containers của docker-compose"""
    path = os.path.expanduser(path)
    cmd = ['docker', 'compose', '-f', path, 'ps']

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise Exception('Docker compose ps timed out (60s)')

    if result.returncode != 0:
        raise Exception(f"Docker compose ps failed: {result.stderr}")

    return {
        'status': 'success',
        'output': result.stdout,
        'stderr': result.stderr,
        'return_code': result.returncode
    }


@app.task(bind=True)
def docker_compose_logs(self, path, service=None, tail=100):
    """Lấy logs từ docker-compose"""
    path = os.path.expanduser(path)
    cmd = ['docker', 'compose', '-f', path, 'logs', '--tail', str(tail)]

    if service:
        cmd.append(service)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise Exception('Docker compose logs timed out (60s)')

    if result.returncode != 0:
        raise Exception(f"Docker compose logs failed: {result.stderr}")

    return {
        'status': 'success',
        'output': result.stdout,
        'stderr': result.stderr,
        'return_code': result.returncode
    }