"""Guide interactif de configuration du téléphone Android."""
print("""
=== ARIA — Configuration du téléphone ===

Étapes à effectuer sur le téléphone :

1. Paramètres > À propos > Numéro de build (taper 7 fois pour activer le mode développeur)
2. Paramètres > Options développeur :
   - Activer le débogage USB
   - Désactiver la mise en veille de l'écran (pendant le chargement)
   - Activer "Rester éveillé"
3. Connecter via USB et accepter l'autorisation ADB sur le téléphone
4. Tester : adb devices

Optionnel (recommandé) :
- Installer Termux pour des actions système plus propres
- Désactiver le verrouillage d'écran (ou utiliser un PIN simple)
- Désactiver les animations (Options développeur > Échelle des animations = 0)

Résolution de l'écran (pour calibrer les taps) :
  adb shell wm size

Tester un tap :
  adb shell input tap 540 1000
""")
