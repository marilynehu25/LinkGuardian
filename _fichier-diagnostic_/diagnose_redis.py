"""Script de diagnostic Redis détaillé"""
import redis
import json

def diagnose_redis():
    """Analyse détaillée de ce qui reste dans Redis"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Connecté à Redis\n")
        
        # Statistiques générales
        total_keys = r.dbsize()
        print(f"📊 Nombre total de clés: {total_keys}\n")
        
        if total_keys == 0:
            print("✨ Redis est vide - pas de tâches en attente\n")
            return
        
        # Analyser les différents types de clés Celery
        print("=" * 70)
        print("ANALYSE DES CLÉS CELERY")
        print("=" * 70)
        
        # 1. Tâches en attente dans la queue
        queue_keys = r.keys('celery')
        if queue_keys:
            print(f"\n🔴 QUEUE 'celery' (tâches en attente):")
            queue_length = r.llen('celery')
            print(f"   Nombre de tâches: {queue_length}")
            
            if queue_length > 0:
                print("\n   📋 Premières tâches dans la queue:")
                tasks = r.lrange('celery', 0, min(5, queue_length - 1))
                for i, task in enumerate(tasks, 1):
                    try:
                        task_data = json.loads(task)
                        task_name = task_data.get('headers', {}).get('task', 'unknown')
                        task_id = task_data.get('headers', {}).get('id', 'unknown')
                        print(f"   {i}. {task_name} (ID: {task_id[:8]}...)")
                    except:
                        print(f"   {i}. {task[:100]}")
        
        # 2. Résultats de tâches
        result_keys = r.keys('celery-task-meta-*')
        if result_keys:
            print(f"\n🟡 RÉSULTATS DE TÂCHES:")
            print(f"   Nombre de résultats stockés: {len(result_keys)}")
            
            print("\n   📊 État des tâches:")
            states = {}
            for key in result_keys[:20]:  # Limiter à 20 pour la démo
                try:
                    result = r.get(key)
                    if result:
                        result_data = json.loads(result)
                        state = result_data.get('status', 'UNKNOWN')
                        states[state] = states.get(state, 0) + 1
                except:
                    pass
            
            for state, count in states.items():
                print(f"      - {state}: {count}")
        
        # 3. Tâches planifiées (scheduled)
        scheduled_keys = r.keys('_kombu.binding.*')
        if scheduled_keys:
            print(f"\n🔵 BINDINGS KOMBU:")
            print(f"   Nombre: {len(scheduled_keys)}")
        
        # 4. Clés "unacked" (non confirmées)
        unacked_keys = r.keys('unacked*')
        if unacked_keys:
            print(f"\n🔴 TÂCHES NON CONFIRMÉES (UNACKED):")
            print(f"   Nombre: {len(unacked_keys)}")
            for key in unacked_keys[:5]:
                length = r.llen(key) if r.type(key) == 'list' else 'N/A'
                print(f"   - {key}: {length}")
        
        # 5. Autres clés
        other_keys = []
        for key in r.keys('*'):
            if not any(pattern in key for pattern in ['celery', '_kombu', 'unacked']):
                other_keys.append(key)
        
        if other_keys:
            print(f"\n🔵 AUTRES CLÉS:")
            for key in other_keys[:10]:
                key_type = r.type(key)
                print(f"   - {key} (type: {key_type})")
        
        print("\n" + "=" * 70)
        print("\n💡 INTERPRÉTATION:")
        
        if queue_length > 0:
            print(f"\n⚠️  PROBLÈME DÉTECTÉ:")
            print(f"   Il y a {queue_length} tâche(s) dans la queue 'celery'")
            print(f"   Ces tâches seront RE-EXÉCUTÉES au prochain démarrage de Celery")
            print(f"\n   Raisons possibles:")
            print(f"   1. Les tâches n'ont jamais été traitées")
            print(f"   2. Le worker Celery a été arrêté avant de les traiter")
            print(f"   3. Configuration task_acks_late=True")
        
        if len(unacked_keys) > 0:
            print(f"\n⚠️  TÂCHES NON CONFIRMÉES:")
            print(f"   Il y a {len(unacked_keys)} tâche(s) non confirmée(s)")
            print(f"   Ces tâches peuvent être re-traitées au redémarrage")
        
        if len(result_keys) > 0:
            print(f"\n✅ RÉSULTATS STOCKÉS:")
            print(f"   {len(result_keys)} résultat(s) en mémoire")
            print(f"   Ces résultats expirent automatiquement (selon config)")
        
        print("\n" + "=" * 70)
        
    except redis.ConnectionError:
        print("❌ Impossible de se connecter à Redis")
        print("   Redis doit être démarré pour ce diagnostic")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    print("=" * 70)
    print("  DIAGNOSTIC DÉTAILLÉ REDIS - LINKGUARDIAN")
    print("=" * 70)
    print()
    diagnose_redis()
    print()
    input("Appuyez sur Entrée pour fermer...")
