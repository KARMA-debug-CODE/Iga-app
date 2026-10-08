# Iga Python playground — press Run (or Ctrl+Enter)
name = input("What is your name? ")
print(f"Muraho, {name}!")

marks = [72, 85, 64, 90]
average = sum(marks) / len(marks)
print("Average mark:", round(average, 1))

for m in marks:
    print(m, "pass" if m >= 50 else "try again")
