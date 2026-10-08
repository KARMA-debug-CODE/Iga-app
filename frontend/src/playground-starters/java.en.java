// Iga Java playground: press Run (or Ctrl+Enter), then answer in the console.
import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        System.out.print("What is your name? ");
        String name = in.hasNextLine() ? in.nextLine() : "friend";
        System.out.println("Muraho, " + name + "!");

        Student[] students = { new Student("Aline", 78), new Student("Eric", 45) };
        for (Student s : students) {
            System.out.println(s.name + ": " + s.result());
        }
    }
}

class Student {
    String name;
    int mark;

    Student(String name, int mark) {
        this.name = name;
        this.mark = mark;
    }

    String result() {
        return mark >= 50 ? "pass" : "try again";
    }
}
