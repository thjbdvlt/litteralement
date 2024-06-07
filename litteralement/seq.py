class Seq:
    """Une séquence numérique incrémentée."""

    def __init__(self):
        """Instancie une séquence."""

        self.curval = 0

    def nextval(self):
        """Retourne la prochaine valeur de la séquence."""

        self.curval += 1
        return self.curval
