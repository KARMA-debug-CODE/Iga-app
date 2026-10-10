---
slug: s5-cs-cpp-classes-objects
language: fr
title: "La programmation orientée objet en C++ : classes et objets"
summary: Représenter des choses réelles par des classes et des objets, leur donner des attributs, des méthodes et des constructeurs, protéger leurs données avec des membres privés, et exécuter un programme BankAccount complet.
reviewed: false
---
## Des structures aux objets

Dans l'unité sur les pointeurs et les structures, vous avez utilisé une `struct` pour regrouper des données qui vont ensemble, comme le nom et la note d'un élève. La **programmation orientée objet (POO)** va un peu plus loin : elle regroupe les données **et** les fonctions qui travaillent sur ces données.

- Une **classe** est un plan. Elle dit quelles données chaque chose possède et ce qu'elle sait faire. Pensez au plan d'une maison : un seul plan, beaucoup de maisons.
- Un **objet** est une chose réelle fabriquée à partir d'une classe. On l'appelle aussi une **instance** de la classe. À partir d'une seule classe `Student`, vous pouvez créer beaucoup d'élèves.
- Un **attribut** (ou donnée membre) est une donnée que possède chaque objet, comme un nom ou un solde.
- Une **méthode** (ou fonction membre) est une fonction placée dans la classe. Elle dit ce que l'objet sait faire, comme `deposit()` ou `show()`.

Chaque objet a sa propre copie des attributs : changer la note d'Aline ne change donc pas celle d'Eric.

## Définir une classe et créer des objets

La définition d'une classe commence par le mot-clé `class`, puis le nom, puis les membres entre accolades. Elle **se termine par un point-virgule**. On crée un objet comme une variable, et on atteint ses membres avec l'**opérateur point** `.`.

### Exemple corrigé 1 : une classe Student

```cpp
#include <iostream>
#include <string>
using namespace std;

class Student {
public:
    string name;
    int mark;

    bool passed() {
        return mark >= 50;
    }

    void show() {
        cout << name << " : " << mark;
        if (passed()) {
            cout << " (réussi)" << endl;
        } else {
            cout << " (à refaire)" << endl;
        }
    }
};

int main() {
    Student a;
    a.name = "Aline";
    a.mark = 78;

    Student b;
    b.name = "Eric";
    b.mark = 46;

    a.show();
    b.show();
    return 0;
}
```

Résultat :

```text
Aline : 78 (réussi)
Eric : 46 (à refaire)
```

Comment cela fonctionne :

1. `class Student { ... };` décrit tous les élèves : deux attributs, `name` et `mark`, et deux méthodes, `passed()` et `show()`.
2. `Student a;` crée un objet appelé `a`. `a.name = "Aline";` donne un nom à cet objet seulement.
3. `a.show()` exécute `show()` pour l'objet `a` : dans la méthode, `name` veut donc dire `a.name`, et `mark` veut dire `a.mark`.
4. `show()` appelle `passed()`. Pour Aline, 78 >= 50 vaut `true`, donc le programme affiche `(réussi)`. Pour Eric, 46 >= 50 vaut `false`.

La ligne `public:` permet au code situé hors de la classe, comme `main()`, d'utiliser ces membres. Nous y revenons plus bas.

## Les constructeurs

Dans l'exemple corrigé 1, chaque objet commence avec un nom vide et une note inconnue, jusqu'à ce qu'on les fixe. Un **constructeur** règle ce problème. C'est une méthode spéciale qui s'exécute automatiquement quand un objet est créé. Elle porte **le même nom que la classe** et n'a **aucun type de retour**, pas même `void`.

Une classe peut avoir plusieurs constructeurs avec des paramètres différents. Un constructeur sans paramètre s'appelle le **constructeur par défaut**.

### Exemple corrigé 2 : deux constructeurs

```cpp
#include <iostream>
#include <string>
using namespace std;

class Student {
public:
    string name;
    int mark;

    Student() {
        name = "Inconnu";
        mark = 0;
    }

    Student(string n, int m) {
        name = n;
        mark = m;
    }

    void show() {
        cout << name << " : " << mark << endl;
    }
};

int main() {
    Student a("Aline", 78);
    Student c;
    a.show();
    c.show();
    return 0;
}
```

Résultat :

```text
Aline : 78
Inconnu : 0
```

1. `Student a("Aline", 78);` appelle le constructeur à deux paramètres : `name` devient `"Aline"` et `mark` devient 78.
2. `Student c;` ne donne aucune valeur : C++ appelle donc le constructeur par défaut. Le nom est `"Inconnu"` et la note est 0.
3. Chaque objet est prêt à servir dès qu'il existe.

## L'encapsulation : public et private

Les **spécificateurs d'accès** décident quel code peut utiliser chaque membre.

| Spécificateur | Qui peut utiliser le membre |
|---|---|
| `public` | n'importe quel code, y compris `main()` |
| `private` | seulement les méthodes de la même classe |

Dans une `class`, les membres sont `private` jusqu'à ce que vous écriviez `public:`. Dans une `struct`, ils sont `public` par défaut.

L'**encapsulation** consiste à garder les données d'un objet `private` et à ne laisser le reste du code les modifier qu'au moyen de méthodes `public`, qui vérifient les règles. Une banque ne laisse pas ses clients écrire le nombre qu'ils veulent dans leur solde : ils font des dépôts et des retraits, et la banque vérifie chacun d'eux. Une méthode qui se contente de renvoyer une valeur privée, comme `getBalance()`, s'appelle un **accesseur** (en anglais *getter*).

### Exemple corrigé 3 : le compilateur protège les données privées

```cpp
#include <iostream>
using namespace std;

class BankAccount {
private:
    int balance;

public:
    BankAccount() {
        balance = 0;
    }

    void deposit(int amount) {
        if (amount > 0) {
            balance += amount;
        }
    }

    int getBalance() {
        return balance;
    }
};

int main() {
    BankAccount acc;
    acc.deposit(5000);
    acc.balance = -1000000;  // interdit : balance est privé
    cout << acc.getBalance() << endl;
    return 0;
}
```

Ce programme ne **compile pas**. Dans l'Atelier de code, g++ s'arrête avec ce message (en anglais) :

```text
error: ‘int BankAccount::balance’ is private within this context
```

1. `balance` est sous `private:` : seules les méthodes de `BankAccount` peuvent donc l'utiliser.
2. `main()` n'est pas une méthode de `BankAccount` : la ligne `acc.balance = -1000000;` est donc refusée avant même que le programme puisse s'exécuter.
3. Supprimez cette ligne : le programme compile et affiche `5000`. La seule façon de changer le solde est `deposit()`, qui ignore les montants qui ne sont pas positifs.

## Un programme complet : BankAccount

Ce programme lit ses données avec `cin`. Pour l'exécuter, ouvrez l'[Atelier de code](/playground), choisissez l'onglet **C++**, remplacez le programme de départ par celui-ci et appuyez sur **Exécuter**. Quand le programme vous attend, tapez votre réponse dans la console et appuyez sur Entrée.

```cpp
#include <iostream>
#include <string>
using namespace std;

class BankAccount {
private:
    string owner;
    int balance;  // en FRW

public:
    BankAccount(string name, int opening) {
        owner = name;
        balance = 0;
        deposit(opening);
    }

    void deposit(int amount) {
        if (amount > 0) {
            balance += amount;
        }
    }

    bool withdraw(int amount) {
        if (amount > 0 && amount <= balance) {
            balance -= amount;
            return true;
        }
        return false;
    }

    int getBalance() {
        return balance;
    }

    string getOwner() {
        return owner;
    }
};

int main() {
    string name;
    int opening, amount;

    cout << "Titulaire du compte : ";
    cin >> name;
    cout << "Dépôt initial (FRW) : ";
    cin >> opening;
    BankAccount account(name, opening);

    cout << "Montant à déposer : ";
    cin >> amount;
    account.deposit(amount);

    cout << "Montant à retirer : ";
    cin >> amount;
    if (account.withdraw(amount)) {
        cout << "Retrait effectué." << endl;
    } else {
        cout << "Refusé : solde insuffisant." << endl;
    }

    cout << account.getOwner() << " a " << account.getBalance() << " FRW." << endl;
    return 0;
}
```

### Exemple corrigé 4 : exécuter BankAccount

Exécutez le programme et répondez Keza, 5000, 2000 et 3500. Suivez `balance` ligne par ligne :

1. `BankAccount account(name, opening);` appelle le constructeur. Il met `balance` à 0, puis appelle `deposit(5000)` : `balance` vaut donc 5000.
2. `account.deposit(amount);` ajoute 2000, car 2000 > 0. `balance` vaut maintenant 7000.
3. `account.withdraw(amount)` retire 3500, car 3500 <= 7000, et renvoie `true`. `balance` vaut maintenant 3500.

Les deux dernières lignes affichées sont `Retrait effectué.` et `Keza a 3500 FRW.`

Exécutez-le encore une fois, mais demandez à retirer 9000. Comme 9000 > 7000, `withdraw()` renvoie `false` et le solde reste à 7000. Le programme affiche `Refusé : solde insuffisant.` puis `Keza a 7000 FRW.`

Remarquez que le constructeur appelle `deposit()`. La règle « seulement des montants positifs » est écrite une seule fois et utilisée partout.

### Exemple corrigé 5 : concevoir une classe

Une entreprise de motos-taxis de Musanze veut un programme pour ses motos. Chaque moto a un numéro de plaque et du carburant dans son réservoir, en litres. On peut faire le plein. Elle ne peut faire un trajet que si elle a assez de carburant, et elle consomme 1 litre tous les 40 km.

1. Trouvez les attributs, ce que chaque moto **possède** : la plaque et le carburant. Rendez-les privés.
2. Trouvez les méthodes, ce qu'une moto **fait** : faire le plein, faire un trajet et nous indiquer son carburant. Rendez-les publiques.
3. Dessinez le **diagramme de classes**. Un signe moins veut dire privé et un signe plus veut dire public.

| Moto |
|---|
| `- plate : string` |
| `- fuel : double` |
| `+ Moto(p : string, f : double)` |
| `+ refuel(litres : double) : void` |
| `+ trip(km : double) : bool` |
| `+ getFuel() : double` |

4. Écrivez la classe, puis testez-la.

```cpp
#include <iostream>
#include <string>
using namespace std;

class Moto {
private:
    string plate;
    double fuel;  // litres dans le réservoir

public:
    Moto(string p, double f) {
        plate = p;
        fuel = f;
    }

    void refuel(double litres) {
        if (litres > 0) {
            fuel += litres;
        }
    }

    bool trip(double km) {
        double needed = km / 40;
        if (needed > fuel) {
            return false;
        }
        fuel -= needed;
        return true;
    }

    double getFuel() {
        return fuel;
    }
};

int main() {
    Moto m("RF 123 A", 2.5);
    for (int i = 0; i < 2; i++) {
        cout << "Trajet de 60 km : " << (m.trip(60) ? "effectué" : "refusé") << endl;
    }
    m.refuel(3);
    cout << "Carburant : " << m.getFuel() << " litres" << endl;
    return 0;
}
```

Résultat :

```text
Trajet de 60 km : effectué
Trajet de 60 km : refusé
Carburant : 4 litres
```

Un trajet de 60 km demande $60 \div 40 = 1{,}5$ litre. Le réservoir contient 2,5 litres : le premier trajet est donc effectué, et il reste $2{,}5 - 1{,}5 = 1$ litre. Le second trajet demande aussi 1,5 litre, mais il ne reste que 1 litre : il est donc refusé. Après `refuel(3)`, le réservoir contient $1 + 3 = 4$ litres.

## Erreurs fréquentes

- **Oublier le point-virgule après la classe.** Une classe doit se terminer par `};`. Sans le `;`, g++ affiche une erreur difficile à comprendre.
- **Donner un type de retour à un constructeur.** `void Student(string n, int m)` n'est pas un constructeur. Écrivez `Student(string n, int m)`.
- **Écrire `Student c();` pour utiliser le constructeur par défaut.** C++ lit cette ligne comme la déclaration d'une fonction. Écrivez `Student c;`.
- **Oublier le constructeur par défaut.** Dès qu'une classe a un constructeur avec des paramètres, `Student c;` ne compile que si vous écrivez aussi `Student()`.
- **Utiliser un membre privé dans `main()`.** Appelez plutôt une méthode publique, comme `getBalance()`.
- **Confondre la classe et l'objet.** Appelez les méthodes sur un objet, comme dans `a.show()`, et non sur la classe, comme dans `Student.show()`.
- **Croire que `cin >>` lit un nom complet.** `cin >> name` s'arrête au premier espace : tapez un seul mot, ou utilisez `getline(cin, name)`.

## Testez-vous

1. Quelle est la différence entre une classe et un objet ?
2. Nommez les deux sortes de membres d'une classe, et donnez un exemple de chacune pour une classe `Phone`.
3. Comment reconnaît-on qu'une méthode est un constructeur ?
4. Que veut dire `private` ? Pourquoi `balance` est-il privé dans `BankAccount` ?
5. Avec la classe `BankAccount` du programme complet, qu'affiche ce code ? `BankAccount acc("Eric", 1000); acc.deposit(-500); acc.withdraw(300); cout << acc.getBalance();`
6. Trouvez les deux erreurs : `class Moto { public: void Moto(string p) { plate = p; } string plate; }`
7. Écrivez la ligne du diagramme de classes pour une méthode publique `area` qui ne prend aucun paramètre et renvoie un `double`.

*Réponses : 1) une classe est le plan ; un objet est une chose fabriquée à partir de ce plan, avec ses propres valeurs · 2) les attributs (les données), comme `battery`, et les méthodes (les actions), comme `call()` · 3) elle porte le même nom que la classe et n'a aucun type de retour · 4) seules les méthodes de la même classe peuvent l'utiliser ; ainsi, le solde ne peut changer qu'au moyen de `deposit()` et de `withdraw()`, qui vérifient chaque montant · 5) `700` : le dépôt de −500 est ignoré, et $1000 - 300 = 700$ · 6) un constructeur n'a pas de type de retour, il faut donc enlever `void` ; et la classe doit se terminer par `};` · 7) `+ area() : double`*
