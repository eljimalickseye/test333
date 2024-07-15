from django.db import models
from django.utils import timezone

class AdMPReport(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    first_name = models.CharField(max_length=100,null=True)
    last_name = models.CharField(max_length=100,null=True)
    full_name = models.CharField(max_length=100,null=True)
    display_name = models.CharField(max_length=100,null=True)
    sam_account_name = models.CharField(max_length=100, null=True) #username
    email_address = models.CharField(max_length=100, null=True)
    account_status = models.CharField(max_length=100,null=True) #status
    initials= models.CharField(max_length=100 , null=True)

    class Meta:
        # Ajouter des contraintes ou des index si nécessaire
        verbose_name = "AdMPReport"
        verbose_name_plural = "AdMPReports"
    
    def __str__(self):
        return self.sam_account_name

class TemporaireDRH(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    matrh = models.CharField(max_length=50)
    logon_name = models.CharField(max_length=100)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    datefin = models.DateField()
    manager = models.CharField(max_length=100)
    hierarchie = models.CharField(max_length=100)

    class Meta:
        # Ajouter des contraintes ou des index si nécessaire
        verbose_name = "TemporaireDRH"
        verbose_name_plural = "TemporairesDRH"

    def __str__(self):
        return self.logon_name

    # Exemple de méthode utilitaire
    def get_full_name(self):
        return f"{self.logon_name}"
    
class CRBT(models.Model):
    user_name = models.CharField(max_length=100,null=True)
    role_id = models.CharField(max_length=100, null=True) #username
    user_type = models.CharField(max_length=100, null=True)
    email_id = models.CharField(max_length=100,null=True) #status

    class Meta:
        # Ajouter des contraintes ou des index si nécessaire
        verbose_name = "CRBT"
        verbose_name_plural = "CRBTs"
    
    def __str__(self):
        return self.user_name
    
from django.db import models

class Extraction_user_pretups(models.Model):
    id = models.AutoField(primary_key=True)
    login_id = models.CharField(max_length=255,null=True, blank=True)
    traitement_fiabilisation = models.CharField(max_length=255,null=True, blank=True)


    def __str__(self):
        return self.login_id
    
class Compte_users_deleted(models.Model):
    id = models.AutoField(primary_key=True)
    login_id = models.CharField(max_length=255,null=True, blank=True)


    def __str__(self):
        return self.login_id
