// Atelier Java d'Iga : appuyez sur Exécuter (ou Ctrl+Entrée), puis répondez dans la console.
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("Comment vous appelez-vous ? ");
        String nom = in.hasNextLine() ? in.nextLine() : "ami";
        System.out.println("Muraho, " + nom + " !");

        Eleve[] eleves = { new Eleve("Aline", 78), new Eleve("Eric", 45) };
        for (Eleve e : eleves) {
            System.out.println(e.nom + " : " + e.resultat());
        }
    }
}

class Eleve {
    String nom;
    int note;

    Eleve(String nom, int note) {
        this.nom = nom;
        this.note = note;
    }

    String resultat() {
        return note >= 50 ? "réussi" : "à retravailler";
    }
}
