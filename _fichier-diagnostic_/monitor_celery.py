"""Monitoring en temps réel de la queue Celery"""
import time
import redis
import json
from datetime import datetime

def monitor_celery_queue(duration_seconds=180):
    """
    Surveille la queue Celery pendant X secondes
    Permet de voir si les tâches sont bien traitées
    """
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Connecté à Redis\n")
        print("=" * 80)
        print(f"MONITORING DE LA QUEUE CELERY - Durée: {duration_seconds}s")
        print("=" * 80)
        print("\nQue surveiller :")
        print("  📊 Queue 'celery' : doit DIMINUER puis devenir VIDE")
        print("  📈 Résultats : doit AUGMENTER")
        print("  ⚠️  Si queue reste pleine → Worker ne traite pas !")
        print("\n" + "-" * 80)
        
        start_time = time.time()
        iteration = 0
        
        while (time.time() - start_time) < duration_seconds:
            iteration += 1
            elapsed = int(time.time() - start_time)
            
            # Mesures
            queue_length = r.llen('celery')
            result_keys = len(r.keys('celery-task-meta-*'))
            unacked_keys = len(r.keys('unacked*'))
            
            # Affichage
            timestamp = datetime.now().strftime('%H:%M:%S')
            status = "🟢 OK" if queue_length == 0 else "🟡 EN COURS" if queue_length < 5 else "🔴 BLOQUÉ"
            
            print(f"\r[{timestamp}] {status} | Queue: {queue_length:3d} | Résultats: {result_keys:3d} | Non-confirmées: {unacked_keys:2d} | {elapsed}s/{duration_seconds}s", end='', flush=True)
            
            time.sleep(2)
        
        print("\n" + "-" * 80)
        print("\n📊 RÉSUMÉ FINAL:")
        
        final_queue = r.llen('celery')
        final_results = len(r.keys('celery-task-meta-*'))
        final_unacked = len(r.keys('unacked*'))
        
        print(f"   Queue finale : {final_queue}")
        print(f"   Résultats stockés : {final_results}")
        print(f"   Tâches non confirmées : {final_unacked}")
        
        print("\n💡 INTERPRÉTATION:")
        
        if final_queue == 0 and final_results > 0:
            print("   ✅ PARFAIT ! Toutes les tâches ont été traitées")
            print("   ✅ Les résultats sont stockés (expirent automatiquement)")
            print("   ✅ Pas de problème de relance au redémarrage")
        elif final_queue > 0:
            print(f"   ⚠️  PROBLÈME : {final_queue} tâche(s) encore dans la queue")
            print("   ⚠️  Ces tâches seront RE-EXÉCUTÉES au redémarrage")
            print("\n   Causes possibles :")
            print("   1. Worker Celery pas démarré ou planté")
            print("   2. Worker surchargé (rate limit)")
            print("   3. Tâches en erreur qui se re-tentent")
        elif final_unacked > 0:
            print(f"   ⚠️  {final_unacked} tâche(s) non confirmée(s)")
            print("   ⚠️  Risque de re-traitement avec task_acks_late=True")
        
        print("\n" + "=" * 80)
        
    except redis.ConnectionError:
        print("❌ Redis n'est pas démarré")
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring interrompu")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")

if __name__ == "__main__":
    print()
    print("🔍 OUTIL DE MONITORING CELERY")
    print()
    print("Cet outil surveille la queue Redis en temps réel.")
    print()
    print("Instructions :")
    print("  1. Démarrez LinkGuardian (Redis + Celery Worker)")
    print("  2. Lancez cet outil")
    print("  3. Importez vos sites dans l'interface")
    print("  4. Observez les changements")
    print()
    
    duration = input("Durée du monitoring en secondes (défaut: 180) : ").strip()
    duration = int(duration) if duration.isdigit() else 180
    
    print()
    monitor_celery_queue(duration)
    print()
    input("Appuyez sur Entrée pour fermer...")
