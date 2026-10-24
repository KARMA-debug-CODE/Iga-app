// La politique de confidentialité, en français (privacy.en.js est le texte anglais ; mêmes sections).
// Un PROJET à faire relire par un avocat avant le lancement (voir privacy.en.js pour les {variables}).
export default {
  title: "Politique de confidentialité",
  intro: [
    "Iga est une application d'apprentissage pour les élèves du secondaire au Rwanda (de la Senior 1 à la Senior 6), leurs enseignants, leurs parents et leurs écoles. Beaucoup de ses utilisateurs sont des enfants.",
    "Cette politique explique simplement quelles données personnelles Iga collecte, pourquoi, où elles sont conservées, qui peut les voir, combien de temps elles sont gardées, et les droits que vous donne la loi rwandaise n° 058/2021 du 13/10/2021 relative à la protection des données à caractère personnel et de la vie privée. Si quelque chose n'est pas clair, posez-nous la question.",
  ],
  sections: [
    {
      id: "controller",
      title: "Qui est responsable",
      body: [
        "{entity} ({address}) gère Iga et en est le responsable du traitement : nous décidons pourquoi et comment vos données personnelles sont utilisées. Votre école décide aussi de certaines choses, par exemple quels enseignants s'occupent de vos classes.",
        "Pour toute question sur vos données personnelles, écrivez à {email} ou utilisez la [page de contact](/contact).",
      ],
    },
    {
      id: "data",
      title: "Ce que nous collectons",
      body: [
        "Nous ne collectons que ce dont Iga a besoin pour fonctionner.",
        {
          list: [
            "Votre compte : nom d'utilisateur, prénom et nom, mot de passe (conservé seulement sous forme d'empreinte sécurisée que personne ne peut lire), rôle (élève, enseignant, parent ou administrateur d'école), classe et combinaison pour les élèves, langue préférée, l'avatar que vous créez et votre adresse e-mail si vous en donnez une. L'adresse e-mail est facultative, sauf pour les administrateurs d'école.",
            "Votre école : l'école que vous choisissez et si elle vous a accepté. Pour une école : son nom, son district, son secteur, son numéro de téléphone et son adresse e-mail.",
            "Votre apprentissage : leçons terminées, laboratoires ouverts, tentatives de quiz et d'examen avec vos réponses et vos notes, notes et commentaires des enseignants, classes rejointes, XP, séries et badges.",
            "Groupes d'étude : les groupes que vous rejoignez, vos messages et notes partagées, et vos signalements de messages.",
            "Questions à Santa, le tuteur IA d'Iga : ce que vous demandez, ce que Santa répond, la leçon ou la matière, et le nombre de questions posées chaque jour. Santa fonctionne sur le serveur d'Iga : vos questions ne sont jamais envoyées à une entreprise d'IA extérieure.",
            "L'espace de code : le nombre de programmes lancés chaque jour et leur durée. Votre code lui-même n'est pas conservé.",
            "Paiements, pour les administrateurs d'école : l'abonnement choisi, le montant, la devise, la date et s'il a été payé. Les paiements par carte et mobile money sont traités par Flutterwave. Nous conservons, chiffrés, la référence du paiement et les informations que Flutterwave nous renvoie (elles peuvent inclure le numéro de téléphone, l'adresse e-mail du payeur et les derniers chiffres d'une carte). Nous ne voyons ni ne conservons jamais de numéro de carte complet ni de code PIN.",
            "Les messages envoyés avec le formulaire de contact : votre nom, votre adresse e-mail, votre école et votre message.",
            "Les traces de sécurité : vos connexions, les connexions échouées, les changements de mot de passe ou d'e-mail, et l'adresse internet (IP) d'où venait une demande.",
          ],
        },
        "Nous ne collectons ni votre date de naissance, ni votre adresse, ni de photos, ni votre position, et Iga n'utilise jamais votre caméra ni votre micro. Nous n'utilisons pas de cookies publicitaires ou de pistage, et nous ne vendons pas de données personnelles.",
      ],
    },
    {
      id: "purposes",
      title: "Pourquoi nous les utilisons",
      body: [
        {
          list: [
            "Pour gérer votre compte et vous montrer vos leçons, laboratoires, quiz et progrès : c'est nécessaire au service que vous, ou votre école, avez demandé.",
            "Pour que les enseignants puissent enseigner : donner du travail, corriger les réponses et suivre les progrès de leurs classes.",
            "Pour que les parents et tuteurs que vous reliez à votre compte puissent suivre vos progrès.",
            "Pour que les écoles puissent gérer leurs membres et payer leur abonnement.",
            "Pour la sécurité d'Iga : empêcher que l'on devine les mots de passe, repérer les abus, et examiner les messages signalés et les conversations avec Santa pour protéger les enfants.",
            "Pour envoyer les e-mails utiles : liens de réinitialisation du mot de passe, avis de suppression de compte et, pour les administrateurs d'école, reçus et rappels d'abonnement.",
            "Pour respecter nos obligations légales, par exemple conserver les justificatifs de paiement pour les impôts.",
            "Pour améliorer Iga avec des chiffres qui ne nomment personne, par exemple le nombre de leçons terminées.",
          ],
        },
        "Aucune décision importante vous concernant n'est prise par une machine seule : les quiz sont corrigés automatiquement à partir des bonnes réponses, et votre enseignant peut les revoir.",
      ],
    },
    {
      id: "children",
      title: "Enfants et consentement des parents",
      body: [
        "La plupart des élèves sur Iga sont des enfants. Selon la loi rwandaise, les données personnelles d'un enfant de moins de 16 ans ne peuvent être traitées qu'avec le consentement d'un parent ou d'un tuteur légal.",
        {
          list: [
            "Quand un élève de moins de 16 ans crée un compte, un parent ou tuteur doit lire avec lui cette politique et les [conditions d'utilisation](/terms) et les accepter. Le formulaire d'inscription demande à l'élève de le confirmer.",
            "Quand un enseignant crée les comptes d'une classe, l'école confirme qu'elle a le consentement des parents ou tuteurs, comme pour ses autres activités. L'élève accepte aussi ces textes à sa première connexion.",
            "Un parent ou tuteur peut suivre les progrès de son enfant en reliant son propre compte avec un code donné dans le profil de l'enfant. Il voit seulement les progrès, jamais les messages.",
            "Un parent ou tuteur peut à tout moment nous demander de voir, corriger ou supprimer les données de son enfant, ou retirer son consentement, en écrivant à {email}.",
          ],
        },
        "Pour protéger les enfants, Iga n'a pas de messages privés : seulement des discussions de groupe que l'on peut signaler et modérer. Les autres élèves voient seulement votre prénom, l'initiale de votre nom, votre avatar et vos XP. Santa ne voit jamais les données des autres élèves.",
      ],
    },
    {
      id: "sharing",
      title: "Qui peut voir vos données",
      body: [
        {
          list: [
            "Vos enseignants, pour les élèves de leurs classes actuelles : nom, nom d'utilisateur, classe, et travaux dans la matière de la classe ou sur leurs devoirs.",
            "Les administrateurs de votre école : les noms, noms d'utilisateur, rôles, classes et statut d'adhésion de leurs membres.",
            "Les parents et tuteurs que vous reliez à votre compte : vos progrès, en lecture seule.",
            "Les autres élèves : votre prénom et votre initiale, votre avatar et vos XP dans les classements et les groupes, et les messages que vous publiez dans vos groupes.",
            "L'équipe Iga : seulement ce qui est nécessaire pour l'assistance, la modération, la protection des enfants (messages signalés et conversations avec Santa) et le bon fonctionnement d'Iga. Chaque consultation de la liste des utilisateurs est enregistrée.",
            "Les entreprises qui travaillent pour nous sous contrat : l'hébergeur de nos serveurs, notre fournisseur d'e-mails pour les e-mails ci-dessus, et Flutterwave pour les paiements. Elles ne peuvent utiliser les données que pour nous fournir leur service.",
            "Les autorités publiques, quand la loi rwandaise l'exige.",
          ],
        },
        "Nous ne vendons ni ne louons de données personnelles, et nous ne les partageons pas avec des annonceurs.",
      ],
    },
    {
      id: "storage",
      title: "Où vos données sont conservées",
      body: [
        "Les données d'Iga sont conservées sur des serveurs situés dans ce pays : {hosting}. Si elles devaient un jour être conservées hors du Rwanda, nous ne le ferions que comme la loi le permet, avec l'autorisation de l'Autorité nationale de cybersécurité (NCSA) et avec une protection au moins aussi forte que celle décrite ici.",
        "Flutterwave traite les informations de paiement dans ses propres systèmes, selon sa propre politique de confidentialité.",
      ],
    },
    {
      id: "retention",
      title: "Combien de temps nous les gardons",
      body: [
        {
          list: [
            "Votre compte et votre apprentissage : tant que votre compte existe. Si vous supprimez votre compte, il est effacé {graceDays} plus tard (voir Vos droits).",
            "Les questions à Santa et ses réponses : {santaDays}.",
            "Les traces de sécurité et d'activité : {auditDays}.",
            "Les comptes journaliers d'utilisation de Santa et de l'espace de code : {usageDays}.",
            "Les messages envoyés avec le formulaire de contact : {contactDays}.",
            "Un mot de passe temporaire donné par un enseignant cesse de fonctionner après {tempDays}.",
            "Les justificatifs de paiement et la comptabilité : aussi longtemps que la loi fiscale et comptable rwandaise l'exige. Ils ne sont jamais supprimés plus tôt, même quand un compte est supprimé : la personne qui a payé apparaît alors seulement comme « Compte supprimé ».",
            "Les sauvegardes : les copies de la base de données sont gardées {backupDays} puis supprimées. Des données supprimées peuvent donc rester dans une sauvegarde pendant au plus {backupDays}.",
          ],
        },
      ],
    },
    {
      id: "rights",
      title: "Vos droits",
      body: [
        "Selon la loi n° 058/2021, vous avez le droit de :",
        {
          list: [
            "Voir vos données : Profil, puis Confidentialité, puis « Télécharger mes données » vous donne un fichier avec tout ce qu'Iga garde sur vous.",
            "Les corriger : modifiez votre nom, votre classe, votre langue et votre adresse e-mail dans votre profil. Pour les informations de classe, demandez à votre enseignant ou à votre école, ou écrivez-nous.",
            "Les supprimer : Profil, puis Confidentialité, puis « Supprimer mon compte ». Votre compte est effacé {graceDays} plus tard, et vous connecter avant annule la suppression.",
            "Vous opposer à l'utilisation de vos données ou demander de la limiter, et retirer votre consentement : écrivez à {email}. Sans consentement, vous ne pourrez peut-être plus utiliser Iga, mais ce qui a été fait avant reste légal.",
            "Emporter vos données ailleurs : le téléchargement est un fichier standard (JSON) que d'autres services peuvent lire.",
            "Porter plainte auprès de l'Autorité nationale de cybersécurité (NCSA), l'autorité rwandaise de protection des données, si vous pensez que nous n'avons pas respecté vos droits.",
          ],
        },
        "Nous répondons aux demandes le plus vite possible, et en moins de 30 jours. Nous pouvons d'abord vous demander de confirmer votre identité. Un parent ou tuteur peut exercer ces droits pour un enfant de moins de 16 ans.",
      ],
    },
    {
      id: "security",
      title: "Comment nous protégeons vos données",
      body: [
        {
          list: [
            "Toutes les connexions à Iga sont chiffrées (HTTPS).",
            "Les mots de passe sont conservés sous forme d'empreintes Argon2id : personne, pas même l'équipe Iga, ne peut les lire.",
            "Les secrets de l'authentification à deux facteurs, les numéros de téléphone des écoles et les informations de paiement sont chiffrés dans la base de données.",
            "Depuis votre profil, vous pouvez activer l'authentification à deux facteurs et vous déconnecter de tous vos appareils.",
            "Chacun voit seulement ce que son rôle permet. Les actions sensibles redemandent le mot de passe et sont enregistrées.",
            "Les tentatives de connexion sont limitées, et des échecs répétés bloquent le compte pendant un moment.",
            "La base de données est sauvegardée chaque jour ; les sauvegardes sont protégées et supprimées après {backupDays}.",
          ],
        },
        "Si un incident de sécurité mettait vos données en danger, nous préviendrions l'Autorité nationale de cybersécurité et, quand la loi l'exige, vous-même.",
      ],
    },
    {
      id: "cookies",
      title: "Cookies et stockage sur votre appareil",
      body: [
        "Iga n'utilise aucun cookie publicitaire, de statistiques ou de pistage. Il garde seulement ce dont il a besoin pour fonctionner :",
        {
          list: [
            "iga_refresh : un cookie qui vous garde connecté jusqu'à {sessionDays}. Les scripts de la page ne peuvent pas le lire, et il est supprimé quand vous vous déconnectez.",
            "iga_team : un cookie réservé aux comptes de l'équipe Iga, pour qu'ils puissent accéder à Iga pendant une mise à jour.",
            "sessionid et csrftoken : des cookies réservés à l'équipe Iga dans l'espace d'administration des contenus.",
            "Dans le stockage de votre navigateur : votre langue, votre thème, si le menu est masqué, les réglages de la calculatrice et, pour qu'Iga fonctionne hors ligne, une copie de votre profil et les leçons que vous avez enregistrées. La déconnexion supprime la copie de votre profil et les leçons enregistrées ; votre langue et vos réglages d'affichage restent.",
            "Vos conversations sur la page Demander à Santa restent seulement dans cet onglet du navigateur, et sont supprimées quand vous vous déconnectez ou fermez l'onglet.",
          ],
        },
        "Comme Iga en a besoin pour fonctionner, ils ne demandent pas de consentement séparé. Vous pouvez les supprimer à tout moment dans les réglages de votre navigateur.",
      ],
    },
    {
      id: "changes",
      title: "Modifications de cette politique",
      body: [
        "Quand nous modifions cette politique de façon importante, nous changeons sa date de version et demandons à chacun de lire et d'accepter la nouvelle version la prochaine fois qu'il utilise Iga.",
      ],
    },
    {
      id: "contact",
      title: "Nous contacter",
      body: ["{entity}, {address}. E-mail : {email}. Vous pouvez aussi utiliser la [page de contact](/contact)."],
    },
  ],
};
