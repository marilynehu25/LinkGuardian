"""Supprimer uniquement les tâches unacked de Redis"""
import redis

def clean_unacked_only():
    """Supprime uniquement les tâches non confirmées"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ Connecté à Redis\n")
        
        # Trouver toutes les clés unacked
        unacked_keys = r.keys('unacked*')
        
        if not unacked_keys:
            print("✅ Aucune tâche 'unacked' trouvée - Redis est propre !\n")
            return
        
        print(f"🔴 Trouvé {len(unacked_keys)} clé(s) 'unacked':\n")
        for key in unacked_keys:
            print(f"   - {key}")
        
        print(f"\n⚠️  Ces tâches sont BLOQUÉES et peuvent causer des re-vérifications")
        print("    au redémarrage.\n")
        
        response = input(f"Voulez-vous supprimer ces {len(unacked_keys)} clé(s) ? (O/N): ")
        
        if response.upper() == 'O':
            deleted = 0
            for key in unacked_keys:
                r.delete(key)
                deleted += 1
                print(f"   ✅ Supprimé: {key}")
            
            print(f"\n🎉 {deleted} clé(s) 'unacked' supprimée(s) avec succès !")
            print("✅ Redis est maintenant propre")
            print("\n💡 Redémarrez LinkGuardian pour appliquer les changements")
        else:
            print("❌ Suppression annulée")
            
    except redis.ConnectionError:
        print("❌ Impossible de se connecter à Redis")
        print("   Redis doit être démarré")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    print("=" * 70)
    print("  NETTOYAGE DES TÂCHES UNACKED - LINKGUARDIAN")
    print("=" * 70)
    print()
    clean_unacked_only()
    print()
    input("Appuyez sur Entrée pour fermer...")
