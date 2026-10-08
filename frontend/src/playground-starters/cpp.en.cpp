// Iga C++ playground: press Run (or Ctrl+Enter), then answer in the console.
#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main() {
    string name;
    cout << "What is your name? ";
    cin >> name;
    cout << "Muraho, " << name << "!" << endl;

    vector<int> marks = {72, 85, 64, 90};
    int total = 0;
    for (int mark : marks) {
        total += mark;
        cout << mark << (mark >= 50 ? " pass" : " try again") << endl;
    }
    cout << "Average mark: " << total / (double)marks.size() << endl;
    return 0;
}
