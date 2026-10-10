-- Atelier SQL d'Iga : appuyez sur Exécuter (ou Ctrl+Entrée)
CREATE TABLE eleves (id INTEGER PRIMARY KEY, nom TEXT, classe TEXT, district TEXT);
CREATE TABLE notes (eleve_id INTEGER, matiere TEXT, note INTEGER);

INSERT INTO eleves VALUES
  (1, 'Aline', 'S2', 'Gasabo'),
  (2, 'Eric', 'S2', 'Huye'),
  (3, 'Grace', 'S3', 'Musanze'),
  (4, 'Jean', 'S3', 'Gasabo');

INSERT INTO notes VALUES
  (1, 'Mathématiques', 78), (1, 'Physique', 64),
  (2, 'Mathématiques', 55), (2, 'Physique', 71),
  (3, 'Mathématiques', 90), (4, 'Physique', 48);

-- Qui habite à Gasabo ?
SELECT nom, classe FROM eleves WHERE district = 'Gasabo';

-- La moyenne de chaque élève, de la meilleure à la moins bonne
SELECT e.nom, ROUND(AVG(n.note), 1) AS moyenne
FROM eleves e JOIN notes n ON n.eleve_id = e.id
GROUP BY e.id
ORDER BY moyenne DESC;
