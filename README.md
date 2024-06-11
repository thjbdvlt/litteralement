littéralement
=============

__littéralement__ est un schéma de base de données [postgresql](https://www.postgresql.org/) conçu pour l'analyse de texte en français et construit selon un modèle générique (EAV) hybride.

le modèle générique que j'utilise comme base, librement emprunté à Francesco Beretta[^1] est plus complet que ce que désigne le terme [EAV](https://en.wikipedia.org/wiki/Entity-attribute-value_model) (_Entity-Attribute-Value_), puisqu'il n'implémente pas seulement une manière de décrire les propriétés des entités, mais aussi, par exemple leurs relations.

des modules écrits et utilisable en Python permettent de facilement importer des données, de les annoter à l'aide de la librairie [spacy](https://spacy.io/) et de remplir la base de données à partir des annotations.

[^1]: Francesco Beretta, "Des sources aux données structurées", 14 octobre 2022, [En ligne](https://wiki-arhn.larhra.fr/lib/exe/fetch.php?media=intro_histoire_numerique:beretta_des_sources_aux_donnees_3-8.pdf), license CC BY-SA 4.0.

modèle EAV hybride
------------------

- une première partie implémente un modèle générique et est destinée à décrire le _monde_ duquel on extrait des textes, qu'il s'agisse des supports matériels des textes, des acteurices sociaux qui les font circuler ou en relisent le contenu, ou encore des événements qui en motive la rédaction. la flexibilité de ce modèle permet de décrire un grand nombre de chose très diverses à l'aide d'un nombre restreint et fixe de tables et de colonnes, et d'ajouter de nouvelles _classes_ ou de nouveaux _types de propriétés_ sans avoir à modifier le schéma[^2].
- la seconde partie de la base de données est, à l'inverse, conçue pour accueillir des données dont la structure est à la fois prévisible et invariable, car l'analyse automatique des textes se fait souvent à l'aide d'outils et de concepts de base non seulement relativement standards, mais aussi uniformément appliqués: qu'on utilise la librairie [spacy](https://spacy.io/), [stanza](https://stanfordnlp.github.io/stanza/) ou [nltk](https://www.nltk.org/), on manipulera toujours des _sentences_ et des _tokens_, lesquels _tokens_ se verront quasi-systématiquement attribués, entre autres choses, un _lemma_ (lemme), un _part-of-speech tag_ (nature), un _dependency label_ (fonction), des caractéristiques morphologiques représentées selon le format [FEATS](https://universaldependencies.org/format.html#morphological-annotation), un _id_ numérique indiquant leur position dans le texte, etc. et s'il y a évidemment différentes _stocks_ de propriétés, le choix d'une méthode d'annotation est généralement adoptée pour l'ensemble du corpus (c'est l'élément _invariable_, lequel permet la comparaison et l'analyse). la flexibilité du modèle EAV est donc inutile pour stocker ces données. comme le modèle EAV engendre par ailleurs des baisses importantes de performances, qu'il requiert un espace de stockage plus grand et qu'en plus il complexifie les requêtes (les rendant moins lisibles), toutes les raisons sont là pour ne pas l'utiliser ici[^3].

[^2]: il est particulièrement utile si l'on ne sait pas, au départ d'une recherche, ce qu'on va exactement collecter et la manière dont on va organiser le résultat de notre collecte (ou de nos analyses), ou la manière dont les objets de notre recherche peuvent se connecter par l'analyse.
[^3]: on évite par exemple de surcharger la table __entité__ avec des millions de mots.

le diagramme ci-dessous représente la structure de la base de données. chaque rectangle représente une table. les flèches traitillées représentent les [héritages](https://www.postgresql.org/docs/current/tutorial-inheritance.html) entre classes: la table __mot__ hérite de la table __token__ qui elle-même hérite de la table __segment__. ainsi, la table mot possède les colonnes __texte__, __debut__ et __fin__[^4]. les autres flèches représentent des _foreign keys_. les lignes commençant par `_` indiquent, elles-aussi des _foreign keys_: la valeur des colonnes en question est toujours `int` ou, pour des raisons d'optimisation, `smallint`, car certaines tables ont peu de chances de dépasser le millier de lignes (typiquement: les _part-of-speech tags_ et _dependency labels_, respectivement stockés dans les tables __nature__ et __fonction__). les colonnes qui commencent par le signe `+` représente des valeurs littérales. si le nom d'une colonne est souligné, cette colonne est utilisée comme _primary key_ (il s'agit toujours de la colonne `id`).

[^4]: les _foreign keys_ (comme, pour le cas de segment, _texte.id_) ne se transmettent par par héritage; elles sont systématiquement ajoutées dans la définition du schéma, ainsi que toutes les autres contraintes.

![](./img/diagram_records.svg)

nlp
---

### mot, lexème

la structure de la partie _nlp_[^5] de la base de données n'est pas spécifique à une librairie, quoi que des modules spécifiques permettent l'analyse avec [spacy](https://spacy.io/). elle est en revanche, peut-être, relativement spécifique à la langue française dans la manière dans la définition de ses objets. en particulier, la table __lexème__ (le mot hors contexte, comme élément du lexique) définit un objet qui regroupe des caractéristiques attribué par [spacy](https://spacy.io/) aux __tokens__, mais qui en français ne varient pas d'un contexte à l'autre. en français, peu importe dans que contexte on trouvera le mot "magiques", il n'agira toujours de l'adjectif (_pos_) "magique" (_lemma_) sous sa forme pluriel (_morphology_), et sa forme canonique (_norm_) sera toujours "magique". il est donc inutile d'attribuer ces quatre propriétés à chaque occurrence du mot "magique": les propriétés __lemme__, __nature__, __norme__ et __morphologie__ sont donc, dans une base de données __littéralement__, des propriétés des __lexèmes__, tandis que les __mots__ ont les propriétés __fonctions__ (_dep_: par exemple "obj"), __noyau__ (_head_), et __lexème__ (la _foreign key du lexème_). l'ensemble des ligne de la table __mot__ constitue donc le _discours_ tandis que l'ensemble des lignes de la table __lexème__ constitue le _lexique_. (de la même manière que dans n'importe quel lexique ou dictionnaire, un même forme graphique peut être utilisée dans différentes entrées lexicale: _être-verbe_, _être-nom_, etc.).

### mot, token

les __mots__ eux-mêmes, par ailleurs, sont également un ajout par rapport aux objets utilisés par [spacy](https://spacy.io/) qui ne différencie pas les différents types de [_tokens_](). or, il n'y a pas de sens à attribuer des __lemmes__ à des signes de ponctuation, à des urls, à des emoticons ou des chiffres, ni à leur associer une __analyse morphologique__ car les chiffres ne sont jamais _au pluriel_ et les URLS ne peuvent pas être fléchies. par ailleurs. ces objets textuels sont, dans une base de données __littéralement__, des __tokens__ mais pas des __mots__, ils n'ont pas de __fonction__ grammaticale ni de __noyau__ (quoi que cela puisse être discutable), ni non plus de __lexème__ (ce qui est en revanche plus légitime à mon avis). de cette façon, le lexique n'est pas pollué par des nombres ou des dates (en nombre virtuellement infini).

### segment

les tables __token__, __mot__, __phrase__ ou __span__ héritent toutes de la table __segment__ qui a trois colonnes: __texte__ (l'identifiant du texte dans lequel le segment se trouve), __debut__ (la position du premier caractère) et __fin__ (la position du dernier caractère).

[^5]: _Natural Language Processing_ (analyse automatique de textes en langage naturel).

eav
---

la table __entité__ regroupe les choses du monde: personnes, lieux, objets matériels, idées, n'importe quoi que l'on veut pouvoir désigner et mettre en relation avec d'autres choses. ses colonnes sont réduites au minimum: un `id` qui permet d'y faire référence et une `classe` qui en définit la nature. la valeur dans la colonne `classe` est l'identifiant (`id`) d'une ligne de la table __classe__ qui contient aussi les colonnes __nom__ (unique et nécessaire) et __définition__ (optionnelle, sans contrainte). la table __classe__ est identique aux tables __type_relation__ et __type_propriete__ (qui ont une position et une fonction identique pour les tables __relation__ et __propriete__). c'est pour quoi elles sont définies dans le diagramme comme étant toutes dérivées d'une table __concept__ (en fait un `type` et non une `table`).

la table __relation__ met en lien deux entités (sujet et objet).

la table __propriete__ permet d'assigner des propriétés aux entités. une propriété peut optionnellement avoir une valeur et cette valeur peut avoir différents _datatype_: le type de propriété "age" requiert une valeur numérique entière (`int`), tandis que la propriété "existe" ne nécessite aucune valeur. la propriété "existe" sera donc placée dans la table __propriété__, qui n'a pas de colonne __val__ tandis que la propriété "age" sera placée dans la table __prop_int__, laquelle table hérite de la table __propriete__ et possède en plus une colonne __val__ dont la valeur est un entier (`int`). naturellement, il est aussi possible d'insérer manuellement des données "age" comme texte dans la table destinée aux valeurs textuelles, ou dans celle qui est dédiée au format `jsonb`. le plus facile, néanmoins, est d'utiliser les modules proposés pour l'importation qui insère automatiquement dans la table appropriée (voir plus bas).

c'est par la table __texte__ que sont mises en lien les deux parties de la base de donneés. elle hérite de la table __propriete__, tout comme les tables __prop_int__ ou __prop_float__ mais elle a également une colonne `id` qui est référencée par la table __segment__ (et toutes les tables qui héritent de __segment__).

importation
-----------

si l'insertion d'entités, de propriétés ou de relations peut évidemment se faire manuellement, il est aussi possible d'importer des données structurées au format JSON comme suit:

```json
{
    "dataset": 1,
    "entites": [
        {"id": 1, "classe": "bibliothèque"},
        {"id": 2, "classe": "lieu", "est_magique": null, "magicité": 1.2},
        {
            "classe": "personne", "nom": "becky", "relations": [
                {"type": "fréquente", "objet": 1}
            ]
        },
        {"classe": "livre", "relations": [{"type": "dans", "objet": 1}]},
    ],
    "relations": [{"type": "est_dans", "objet": 2, "sujet": 1}]
}
```

le seul champ requis est, dans chaque entité, le champ `classe`. le champ `id` permet de définir les relations entre les entités et ne correspond pas à l'`id` de l'entité dans la base de données: il ne doit être unique que dans un `dataset` (spécifié dans le champ `dataset`). dans les entités, tous les champs qui ne sont pas `classe`, `id` ou `relations` sont interprétés comme des propriétés et sont insérées dans les tables qui correspondent au `datatype`:

```python
{"est_magique": None}  # ira dans la table propriete, sans valeur
{"nom": "becky"}       # ira dans la table texte
{"nom": 1231}          # ira dans la table prop_int
{"nom": 1.2}          # ira dans la table prop_float
{"noms": {"prénom": "!", "nom": "?"}}  # ira dans la table prop_json
```

l'importation se fait en ajoutant dans la table `import._data` des données au format décrit ci-dessus et en appelant la fonction `importer` qui se trouve dans le module `litteralement.eav.ajout`:

```python
import psycopg
import litteralement.eav.ajout

dbname = "litteralement"
conn = psycopg.connect(dbname=dbname)
litteralement.eav.ajout.importer()
```
