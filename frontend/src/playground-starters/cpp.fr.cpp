// Atelier C++ d'Iga : appuyez sur Exécuter (ou Ctrl+Entrée), puis répondez dans la console.
#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main() {
    string nom;
    cout << "Comment vous appelez-vous ? ";
    cin >> nom;
    cout << "Muraho, " << nom << " !" << endl;

    vector<int> notes = {72, 85, 64, 90};
    int total = 0;
    for (int note : notes) {
        total += note;
        cout << note << (note >= 50 ? " réussi" : " à retravailler") << endl;
    }
    cout << "Note moyenne : " << total / (double)notes.size() << endl;
    return 0;
}
