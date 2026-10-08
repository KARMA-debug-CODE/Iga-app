-- Iga SQL playground: press Run (or Ctrl+Enter)
CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, grade TEXT, district TEXT);
CREATE TABLE marks (student_id INTEGER, subject TEXT, mark INTEGER);

INSERT INTO students VALUES
  (1, 'Aline', 'S2', 'Gasabo'),
  (2, 'Eric', 'S2', 'Huye'),
  (3, 'Grace', 'S3', 'Musanze'),
  (4, 'Jean', 'S3', 'Gasabo');

INSERT INTO marks VALUES
  (1, 'Mathematics', 78), (1, 'Physics', 64),
  (2, 'Mathematics', 55), (2, 'Physics', 71),
  (3, 'Mathematics', 90), (4, 'Physics', 48);

-- Who lives in Gasabo?
SELECT name, grade FROM students WHERE district = 'Gasabo';

-- Each student's average mark, best first
SELECT s.name, ROUND(AVG(m.mark), 1) AS average
FROM students s JOIN marks m ON m.student_id = s.id
GROUP BY s.id
ORDER BY average DESC;
