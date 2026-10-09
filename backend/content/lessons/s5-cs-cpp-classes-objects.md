---
slug: s5-cs-cpp-classes-objects
subject: computer-science
grade: S5
unit: 7
order: 1
title: "Object-oriented programming in C++: classes and objects"
summary: Model real things with classes and objects, give them attributes, methods and constructors, protect their data with private members, and run a complete BankAccount program.
minutes: 50
simulations:
---
## From structures to objects

In the unit on pointers and structures, you used a `struct` to keep related data together, such as a student's name and mark. **Object-oriented programming (OOP)** goes one step further: it keeps the data **and** the functions that work on that data together.

- A **class** is a plan. It says what data each thing has and what it can do. Think of the plan of a house: one plan, many houses.
- An **object** is one real thing made from a class. It is also called an **instance** of the class. From one `Student` class you can make many students.
- An **attribute** (or data member) is a piece of data that each object holds, such as a name or a balance.
- A **method** (or member function) is a function inside the class. It says what the object can do, such as `deposit()` or `show()`.

Every object has its own copy of the attributes, so changing Aline's mark does not change Eric's.

## Defining a class and making objects

A class definition starts with the keyword `class`, then the name, then the members between braces. It **ends with a semicolon**. You create an object like a variable, and you reach its members with the **dot operator** `.`.

### Worked example 1: a Student class

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
        cout << name << ": " << mark;
        if (passed()) {
            cout << " (pass)" << endl;
        } else {
            cout << " (try again)" << endl;
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

Output:

```text
Aline: 78 (pass)
Eric: 46 (try again)
```

How it works:

1. `class Student { ... };` describes every student: two attributes, `name` and `mark`, and two methods, `passed()` and `show()`.
2. `Student a;` creates an object called `a`. `a.name = "Aline";` sets the name of that object only.
3. `a.show()` runs `show()` for object `a`, so inside the method, `name` means `a.name` and `mark` means `a.mark`.
4. `show()` calls `passed()`. For Aline, 78 >= 50 is `true`, so it prints `(pass)`. For Eric, 46 >= 50 is `false`.

The line `public:` lets code outside the class, such as `main()`, use these members. We come back to it below.

## Constructors

In Worked example 1, each object starts with an empty name and an unknown mark until we set them. A **constructor** fixes this. It is a special method that runs automatically when an object is created. It has the **same name as the class** and **no return type**, not even `void`.

A class can have several constructors with different parameters. A constructor with no parameters is called the **default constructor**.

### Worked example 2: two constructors

```cpp
#include <iostream>
#include <string>
using namespace std;

class Student {
public:
    string name;
    int mark;

    Student() {
        name = "Unknown";
        mark = 0;
    }

    Student(string n, int m) {
        name = n;
        mark = m;
    }

    void show() {
        cout << name << ": " << mark << endl;
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

Output:

```text
Aline: 78
Unknown: 0
```

1. `Student a("Aline", 78);` calls the constructor with two parameters, so `name` becomes `"Aline"` and `mark` becomes 78.
2. `Student c;` gives no values, so C++ calls the default constructor: the name is `"Unknown"` and the mark is 0.
3. Every object is ready to use from the moment it exists.

## Encapsulation: public and private

**Access specifiers** decide which code may use each member.

| Specifier | Who can use the member |
|---|---|
| `public` | any code, including `main()` |
| `private` | only the methods of the same class |

In a `class`, members are `private` until you write `public:`. In a `struct`, they are `public` by default.

**Encapsulation** means keeping an object's data `private` and letting other code change it only through `public` methods, which check the rules. A bank does not let customers write any number they like into their balance: they make deposits and withdrawals, and the bank checks each one. A method that only gives back a private value, like `getBalance()`, is called a **getter**.

### Worked example 3: the compiler protects private data

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
    acc.balance = -1000000;  // not allowed: balance is private
    cout << acc.getBalance() << endl;
    return 0;
}
```

This program does **not** compile. In the Code playground, g++ stops with this message:

```text
error: ‘int BankAccount::balance’ is private within this context
```

1. `balance` is under `private:`, so only the methods of `BankAccount` may use it.
2. `main()` is not a method of `BankAccount`, so the line `acc.balance = -1000000;` is refused before the program can even run.
3. Delete that line and the program compiles and prints `5000`. The only way to change the balance is `deposit()`, which ignores amounts that are not positive.

## A complete program: BankAccount

This program reads its input with `cin`. To run it, open the [Code playground](/playground), choose the **C++** tab, replace the starter program with this one and press **Run**. When the program waits for you, type your answer in the console and press Enter.

```cpp
#include <iostream>
#include <string>
using namespace std;

class BankAccount {
private:
    string owner;
    int balance;  // in FRW

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

    cout << "Account owner: ";
    cin >> name;
    cout << "Opening deposit (FRW): ";
    cin >> opening;
    BankAccount account(name, opening);

    cout << "Amount to deposit: ";
    cin >> amount;
    account.deposit(amount);

    cout << "Amount to withdraw: ";
    cin >> amount;
    if (account.withdraw(amount)) {
        cout << "Withdrawal done." << endl;
    } else {
        cout << "Refused: not enough money." << endl;
    }

    cout << account.getOwner() << " has " << account.getBalance() << " FRW." << endl;
    return 0;
}
```

### Worked example 4: running BankAccount

Run the program and answer Keza, 5000, 2000 and 3500.

| Line in `main()` | What happens | `balance` |
|---|---|---|
| `BankAccount account(name, opening);` | the constructor sets 0, then calls `deposit(5000)` | 5000 |
| `account.deposit(amount);` | 2000 > 0, so it is added | 7000 |
| `account.withdraw(amount)` | 3500 <= 7000, so it is taken away and the method returns `true` | 3500 |

The last two lines printed are `Withdrawal done.` and `Keza has 3500 FRW.`

Now run it again, but ask to withdraw 9000. Since 9000 > 7000, `withdraw()` returns `false` and the balance stays 7000. The program prints `Refused: not enough money.` and then `Keza has 7000 FRW.`

Notice that the constructor calls `deposit()`. The rule "only positive amounts" is written once and used everywhere.

### Worked example 5: designing a class

A moto-taxi company in Musanze wants a program for its motos. Each moto has a plate number and some fuel in its tank, in litres. It can be refuelled. It can make a trip only if it has enough fuel, and it uses 1 litre for every 40 km.

1. Find the attributes, what each moto **has**: the plate and the fuel. Make them private.
2. Find the methods, what a moto **does**: refuel, make a trip, and tell us its fuel. Make them public.
3. Draw the **class diagram**. A minus sign means private and a plus sign means public.

| Moto |
|---|
| `- plate : string` |
| `- fuel : double` |
| `+ Moto(p : string, f : double)` |
| `+ refuel(litres : double) : void` |
| `+ trip(km : double) : bool` |
| `+ getFuel() : double` |

4. Write the class, then test it.

```cpp
#include <iostream>
#include <string>
using namespace std;

class Moto {
private:
    string plate;
    double fuel;  // litres in the tank

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
        cout << "Trip of 60 km: " << (m.trip(60) ? "done" : "refused") << endl;
    }
    m.refuel(3);
    cout << "Fuel: " << m.getFuel() << " litres" << endl;
    return 0;
}
```

Output:

```text
Trip of 60 km: done
Trip of 60 km: refused
Fuel: 4 litres
```

A 60 km trip needs $60 \div 40 = 1.5$ litres. The tank holds 2.5 litres, so the first trip is done and $2.5 - 1.5 = 1$ litre is left. The second trip also needs 1.5 litres, but only 1 is left, so it is refused. After `refuel(3)`, the tank holds $1 + 3 = 4$ litres.

## Common mistakes

- **Forgetting the semicolon after the class.** A class must end with `};`. Without the `;`, g++ reports an error that is hard to understand.
- **Giving a constructor a return type.** `void Student(string n, int m)` is not a constructor. Write `Student(string n, int m)`.
- **Writing `Student c();` to use the default constructor.** C++ reads this as the declaration of a function. Write `Student c;`.
- **Forgetting the default constructor.** Once a class has a constructor with parameters, `Student c;` only compiles if you also write `Student()`.
- **Using a private member in `main()`.** Call a public method, such as `getBalance()`, instead.
- **Mixing up the class and the object.** Call methods on an object, as in `a.show()`, not on the class, as in `Student.show()`.
- **Expecting `cin >>` to read a full name.** `cin >> name` stops at the first space, so type one word, or use `getline(cin, name)`.

## Check yourself

1. What is the difference between a class and an object?
2. Name the two kinds of members a class has, and give an example of each for a `Phone` class.
3. How can you tell that a method is a constructor?
4. What does `private` mean? Why is `balance` private in `BankAccount`?
5. Using the `BankAccount` class from the complete program, what does this print? `BankAccount acc("Eric", 1000); acc.deposit(-500); acc.withdraw(300); cout << acc.getBalance();`
6. Find the two mistakes: `class Moto { public: void Moto(string p) { plate = p; } string plate; }`
7. Write the class diagram line for a public method `area` that takes no parameters and returns a `double`.

*Answers: 1) a class is the plan; an object is one thing made from that plan, with its own values · 2) attributes (data), such as `battery`, and methods (actions), such as `call()` · 3) it has the same name as the class and no return type · 4) only the methods of the same class can use it; so the balance can only change through `deposit()` and `withdraw()`, which check every amount · 5) `700`: the deposit of −500 is ignored, and $1000 - 300 = 700$ · 6) a constructor has no return type, so remove `void`; and the class must end with `};` · 7) `+ area() : double`*
