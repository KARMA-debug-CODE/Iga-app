# Atelier Python d'Iga — appuyez sur Exécuter (ou Ctrl+Entrée)
nom = input("Comment vous appelez-vous ? ")
print(f"Muraho, {nom} !")

notes = [72, 85, 64, 90]
moyenne = sum(notes) / len(notes)
print("Note moyenne :", round(moyenne, 1))

for n in notes:
    print(n, "réussi" if n >= 50 else "à retravailler")
