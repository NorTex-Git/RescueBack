from datetime import datetime, timedelta
import random
import shutil
import time
from services.empresa_service import EmpresaService
from services.usuario_service import UsuarioService
from services.activity_service import ActivityService
from services.hardware_service import HardwareService
from services.tipo_empresa_service import TipoEmpresaService
from repositories.empresa_repository import EmpresaRepository
from repositories.usuario_repository import UsuarioRepository
from repositories.hardware_repository import HardwareRepository
from repositories.mqtt_alert_repository import MqttAlertRepository
from repositories.activity_repository import ActivityRepository
from repositories.session_repository import SessionRepository
from utils.performance_metrics import get_performance_metrics

class SuperAdminDashboardService:
    """Service para el Super Admin Dashboard"""
    
    def __init__(self):
        self.empresa_service = EmpresaService()
        self.usuario_service = UsuarioService()
        self.activity_service = ActivityService()
        self.hardware_service = HardwareService()
        self.tipo_empresa_service = TipoEmpresaService()
        self.empresa_repository = EmpresaRepository()
        self.usuario_repository = UsuarioRepository()
        self.hardware_repository = HardwareRepository()
        self.activity_repository = ActivityRepository()
        self.session_repository = SessionRepository()
        self.alert_repository = MqttAlertRepository()

    def _get_alerts_stats(self, days=30):
        """Total de alertas y desglose por severidad de los últimos `days` días."""
        por = {'critica': 0, 'alta': 0, 'media': 0, 'baja': 0}
        try:
            since = datetime.utcnow() - timedelta(days=days)
            pipeline = [
                {'$match': {'fecha_creacion': {'$gte': since}}},
                {'$group': {
                    '_id': {'$toLower': {'$ifNull': ['$prioridad', 'media']}},
                    'n': {'$sum': 1},
                }},
            ]
            total = 0
            for row in self.alert_repository.collection.aggregate(pipeline):
                key = (row.get('_id') or 'media')
                n = row.get('n', 0)
                total += n
                if 'crit' in key:
                    por['critica'] += n
                elif 'alta' in key:
                    por['alta'] += n
                elif 'baja' in key:
                    por['baja'] += n
                else:
                    por['media'] += n
            return {'total': total, 'por_severidad': por}
        except Exception:
            return {'total': 0, 'por_severidad': por}

    def get_dashboard_stats(self):
        """Obtiene estadísticas generales del dashboard"""
        try:
            # Obtener estadísticas de empresas
            empresas_stats = self.empresa_service.get_empresa_stats()
            
            # Obtener estadísticas de usuarios
            users_stats = self._get_users_stats()
            
            # Obtener estadísticas de hardware
            hardware_stats = self._get_hardware_stats()
            
            # Generar datos de rendimiento (mock)
            performance = random.randint(75, 95)
            avg_performance = random.randint(65, 85)
            
            alerts_stats = self._get_alerts_stats(30)

            if empresas_stats['success'] and users_stats['success'] and hardware_stats['success']:
                data = {
                    'total_empresas': empresas_stats['data']['total_general'],
                    'active_empresas': empresas_stats['data']['total_activas'],
                    'total_users': users_stats['data']['total'],
                    # Alias que espera el frontend del dashboard.
                    'total_usuarios': users_stats['data']['total'],
                    'active_users': users_stats['data']['active'],
                    'total_hardware': hardware_stats['data']['total_items'],
                    'available_hardware': hardware_stats['data']['available_items'],
                    'total_alertas': alerts_stats['total'],
                    'alertas_por_severidad': alerts_stats['por_severidad'],
                    'performance': performance,
                    'avg_performance': avg_performance
                }
                return {'success': True, 'data': data}
            
            return {'success': False, 'errors': ['Error al obtener estadísticas generales del sistema']}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def _get_users_stats(self):
        """Obtiene estadísticas de usuarios"""
        try:
            total_users = self.usuario_repository.count_all()
            active_users = self.usuario_repository.count_active()
            
            return {
                'success': True,
                'data': {
                    'total': total_users,
                    'active': active_users,
                    'inactive': total_users - active_users
                }
            }
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def _get_hardware_stats(self):
        """Obtiene estadísticas de hardware"""
        try:
            hardware_result = self.hardware_service.get_all_hardware_including_inactive()
            
            if hardware_result['success']:
                hardware_list = hardware_result['data']
                total_items = len(hardware_list)
                available_items = len([h for h in hardware_list if h.get('activa', True)])
                
                return {
                    'success': True,
                    'data': {
                        'total_items': total_items,
                        'available_items': available_items,
                        'out_of_stock': total_items - available_items
                    }
                }
            else:
                return {'success': False, 'errors': ['Error al obtener estadísticas de hardware']}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def get_recent_companies(self, limit=5):
        """Obtiene empresas recientes"""
        try:
            empresas_result = self.empresa_service.get_all_empresas(include_inactive=True)
            
            if empresas_result['success']:
                empresas = empresas_result['data']
                
                # Ordenar por fecha de creación descendente
                empresas_sorted = sorted(empresas, 
                                       key=lambda x: x.get('fecha_creacion', ''), 
                                       reverse=True)
                
                # Tomar solo las más recientes
                recent_empresas = empresas_sorted[:limit]
                
                # Formatear datos para el frontend
                formatted_companies = []
                for empresa in recent_empresas:
                    formatted_companies.append({
                        'id': empresa['_id'],
                        'name': empresa['nombre'],
                        'industry': empresa.get('descripcion', 'Tecnología'),
                        'members_count': random.randint(5, 75),  # Mock data
                        'status': 'active' if empresa.get('activa', True) else 'inactive',
                        'created_at': empresa.get('fecha_creacion', ''),
                        'revenue': random.randint(50000, 2000000),  # Mock data
                        'growth_rate': round(random.uniform(-5.0, 25.0), 1)  # Mock data
                    })
                
                return {'success': True, 'data': formatted_companies}
            else:
                return {'success': False, 'errors': ['Error al obtener empresas recientes']}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def get_recent_users(self, limit=5):
        """Obtiene usuarios recientes"""
        try:
            # Obtener usuarios de todas las empresas
            empresas_result = self.empresa_service.get_all_empresas(include_inactive=True)
            
            if not empresas_result['success']:
                return {'success': False, 'errors': ['Error al obtener empresas']}
            
            all_users = []
            for empresa in empresas_result['data']:
                users_result = self.usuario_service.get_usuarios_by_empresa_including_inactive(empresa['_id'])
                if users_result['success']:
                    for user in users_result['data']:
                        user['empresa_nombre'] = empresa['nombre']
                        all_users.append(user)
            
            # Ordenar por fecha de creación descendente
            users_sorted = sorted(all_users, 
                                key=lambda x: x.get('fecha_creacion', ''), 
                                reverse=True)
            
            # Tomar solo los más recientes
            recent_users = users_sorted[:limit]
            
            # Formatear datos para el frontend
            formatted_users = []
            for user in recent_users:
                formatted_users.append({
                    'id': user['_id'],
                    'name': user['nombre'],
                    'email': user.get('email', f"{user['nombre'].lower().replace(' ', '.')}@example.com"),
                    'role': user.get('rol', 'user'),
                    'status': 'active' if user.get('activo', True) else 'inactive',
                    'joined_at': user.get('fecha_creacion', ''),
                    'company': user.get('empresa_nombre', 'N/A'),
                    'last_login': (datetime.now() - timedelta(days=random.randint(0, 7))).strftime('%Y-%m-%d'),
                    'tasks_completed': random.randint(5, 50)  # Mock data
                })
            
            return {'success': True, 'data': formatted_users}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def get_activity_chart_data(self, period='30d', limit=8):
        """Obtiene datos REALES para gráfico de actividad basados en activity logs"""
        try:
            # Convertir período a días
            period_days = {
                '24h': 1,
                '7d': 7,
                '30d': 30
            }.get(period, 30)
            
            # Obtener empresas activas
            empresas_result = self.empresa_service.get_all_empresas(include_inactive=False)
            
            if not empresas_result['success']:
                return {'success': False, 'errors': ['Error al obtener empresas']}
            
            # Obtener estadísticas de actividad por empresa
            activity_stats = self.activity_repository.get_activity_stats_by_empresa(period_days)
            
            # Crear diccionario de actividad por empresa_id - SOLO para empresas activas
            empresas_activas = empresas_result['data']
            empresas_activas_ids = {empresa['_id'] for empresa in empresas_activas}
            
            activity_by_empresa = {}
            for stat in activity_stats:
                empresa_id = str(stat['_id'])
                # Solo incluir actividad si la empresa está activa
                if empresa_id in empresas_activas_ids:
                    activity_by_empresa[empresa_id] = stat['count']
                else:
                    # print(f"⚠️ Skipping activity for inactive empresa: {empresa_id}")
                    pass
            
            # Preparar datos para el gráfico - ORDENAR POR ACTIVIDAD
            empresas = empresas_result['data']
            
            # Crear lista de empresas con su actividad
            empresas_with_activity = []
            for empresa in empresas:
                empresa_id = empresa['_id']
                activity_count = activity_by_empresa.get(empresa_id, 0)
                empresas_with_activity.append({
                    'empresa': empresa,
                    'activity_count': activity_count
                })
            
            # Ordenar por actividad (mayor a menor) y tomar el TOP
            empresas_with_activity.sort(key=lambda x: x['activity_count'], reverse=True)
            top_empresas = empresas_with_activity[:limit]
            
            # Generar labels y data para el gráfico
            labels = []
            data = []
            
            for item in top_empresas:
                empresa = item['empresa']
                activity_count = item['activity_count']
                labels.append(empresa['nombre'])
                data.append(activity_count)
                
            # Debug: mostrar el ranking
            # print(f"🏆 TOP {limit} empresas por actividad:")
            for i, item in enumerate(top_empresas, 1):
                empresa_nombre = item['empresa']['nombre']
                activity_count = item['activity_count']
                # print(f"   {i}. {empresa_nombre}: {activity_count} logs")
            
            # Si no hay empresas, devolver estructura vacía
            if not labels:
                return {
                    'success': True,
                    'data': {
                        'labels': ['Sin empresas'],
                        'datasets': [{
                            'label': f'Actividad ({period})',
                            'data': [0],
                            'backgroundColor': ['#9CA3AF'],
                            'borderWidth': 2
                        }]
                    }
                }
            
            chart_data = {
                'labels': labels,
                'datasets': [{
                    'label': f'Actividad ({period})',
                    'data': data,
                    'backgroundColor': [
                        '#8b5cf6', '#f472b6', '#60a5fa', '#34d399', 
                        '#fbbf24', '#ef4444', '#06b6d4', '#84cc16'
                    ][:len(data)],  # Solo usar los colores necesarios
                    'borderWidth': 2
                }]
            }
            
            return {'success': True, 'data': chart_data}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def get_distribution_chart_data(self):
        """Obtiene datos REALES para gráfico de distribución basados en tipos de empresa"""
        try:
            # Obtener distribución real de empresas por tipo
            distribution_result = self.tipo_empresa_service.get_empresas_distribution_by_tipo()
            
            if distribution_result['success']:
                return distribution_result
            else:
                # Si hay error, devolver datos de fallback
                return {
                    'success': True,
                    'data': {
                        'labels': ['Sin datos'],
                        'datasets': [{
                            'data': [0],
                            'backgroundColor': ['#9CA3AF'],
                            'borderWidth': 2,
                            'borderColor': '#ffffff'
                        }]
                    }
                }
                
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def get_hardware_stats(self):
        """Obtiene estadísticas detalladas de hardware"""
        try:
            hardware_result = self.hardware_service.get_all_hardware_including_inactive()
            
            if hardware_result['success']:
                hardware_list = hardware_result['data']
                
                total_items = len(hardware_list)
                available_items = len([h for h in hardware_list if h.get('activa', True)])
                out_of_stock = total_items - available_items
                
                # Distribución por tipo
                type_distribution = {}
                for hardware in hardware_list:
                    hw_type = hardware.get('tipo', 'Unknown')
                    type_distribution[hw_type] = type_distribution.get(hw_type, 0) + 1
                
                # Convertir a formato que espera el frontend
                by_type = []
                for tipo, cantidad in type_distribution.items():
                    by_type.append({
                        'nombre': tipo,
                        'count': cantidad
                    })
                
                stats = {
                    'total_items': total_items,
                    'available_items': available_items,
                    'out_of_stock': out_of_stock,
                    'discontinued': 0,  # Mock data
                    'total_value': random.randint(500000, 2000000),  # Mock data
                    'avg_price': random.randint(3000, 8000),  # Mock data
                    'type_distribution': type_distribution,
                    'by_type': by_type  # Para compatibilidad con frontend
                }
                
                return {'success': True, 'data': stats}
            else:
                return {'success': False, 'errors': ['Error al obtener estadísticas de hardware']}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def get_system_performance(self):
        """Obtiene métricas de rendimiento del sistema"""
        try:
            uptime_percentage = self._get_uptime_percentage()
            response_time = self._get_average_response_time_ms()
            error_rate = self._get_error_rate_percentage()
            session_stats = self._get_session_stats()
            cpu_usage = self._get_cpu_usage_percentage()
            memory_usage = self._get_memory_usage_percentage()
            disk_usage = self._get_disk_usage_percentage()

            performance_data = {
                'uptime_percentage': uptime_percentage,
                'response_time': response_time,  # milliseconds
                'error_rate': error_rate,  # percentage
                'active_sessions': session_stats.get('active_sessions', 0),
                'avg_session_duration': session_stats.get('avg_session_duration', 0),  # minutes
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage
            }
            
            return {'success': True, 'data': performance_data}
        except Exception as e:
            return {'success': False, 'errors': [str(e)]}

    def _get_uptime_percentage(self, window_seconds=86400):
        try:
            with open('/proc/uptime', 'r', encoding='utf-8') as uptime_file:
                uptime_seconds = float(uptime_file.read().split()[0])
            percentage = min(100.0, (uptime_seconds / window_seconds) * 100)
            return round(percentage, 2)
        except Exception:
            return 0

    def _get_average_response_time_ms(self):
        metrics = get_performance_metrics()
        return int(round(metrics.get_average_response_time_ms()))

    def _get_error_rate_percentage(self):
        metrics = get_performance_metrics()
        return round(metrics.get_error_rate_percentage(), 2)

    def _get_session_stats(self):
        try:
            result = self.session_repository.get_active_session_duration_stats()
            if result['success']:
                return result['data']
        except Exception:
            pass
        return {'active_sessions': 0, 'avg_session_duration': 0}

    def _get_cpu_usage_percentage(self):
        try:
            def read_cpu_times():
                with open('/proc/stat', 'r', encoding='utf-8') as stat_file:
                    fields = stat_file.readline().split()[1:]
                times = [int(field) for field in fields]
                idle = times[3] + times[4]
                total = sum(times)
                return idle, total

            idle_1, total_1 = read_cpu_times()
            time.sleep(0.1)
            idle_2, total_2 = read_cpu_times()

            idle_delta = idle_2 - idle_1
            total_delta = total_2 - total_1
            if total_delta == 0:
                return 0
            usage = (1 - (idle_delta / total_delta)) * 100
            return round(usage, 1)
        except Exception:
            return 0

    def _get_memory_usage_percentage(self):
        try:
            meminfo = {}
            with open('/proc/meminfo', 'r', encoding='utf-8') as mem_file:
                for line in mem_file:
                    key, value = line.split(':', 1)
                    meminfo[key] = int(value.strip().split()[0])
            total = meminfo.get('MemTotal', 0)
            available = meminfo.get('MemAvailable', 0)
            if total == 0:
                return 0
            used = total - available
            return round((used / total) * 100, 1)
        except Exception:
            return 0

    def _get_disk_usage_percentage(self):
        try:
            usage = shutil.disk_usage('/')
            if usage.total == 0:
                return 0
            return round((usage.used / usage.total) * 100, 1)
        except Exception:
            return 0
