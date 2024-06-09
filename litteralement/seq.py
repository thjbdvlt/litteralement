class Seq:
    """Une séquence numérique auto-incrémentée."""

    def __init__(self, start=0):
        """Instancie une séquence."""

        self.curval = start

    def nextval(self):
        """Retourne la prochaine valeur de la séquence.

        Returns (int)
        """

        self.curval += 1
        return self.curval
