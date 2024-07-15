from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm
from django.db import connection
import mysql.connector
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import AdMPReport, TemporaireDRH, CRBT, Extraction_user_pretups,Compte_users_deleted
from zoom.models import Extraction_zoom
from datetime import datetime, timedelta
from django.utils import timezone
from dateutil import parser
from datetime import date
from django.db import transaction
from django.db import IntegrityError
from django.http import HttpResponse
import csv
import pandas as pd
from .forms import Upload
from django.apps import apps
from django.db import connections
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from django.db.models import Q
from django.contrib.auth.forms import AuthenticationForm
import mysql.connector
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return render(request, 'home.html')

def connect_to_database():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin",
        database="fiable"
    )
    return connection  # Retourne le nom de la base de données au lieu de l'objet de connexion

def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            print(f'Trying to authenticate user: {username}')
            user = authenticate(username=username, password=password)
            if user is not None:
                print('Authentication successful')
                login(request, user)
                return redirect('home')  # Remplacez 'home' par la vue souhaitée après connexion
            else:
                print('Authentication failed')
                return render(request, 'home.html', {'form': form, 'error': 'Invalid username or password'})
        else:
            print('Form is not valid')
            return render(request, 'home.html', {'form': form, 'error': 'Invalid username or password'})
    else:
        form = AuthenticationForm()
        return render(request, 'home.html', {'form': form})


def logout_user(request):
    logout(request)
    messages.success(request, "You Have Been Logged Out...")
    return redirect('login_user')


def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
        # Authenticate et Login
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, "You Have Successfully Registered!")
            return redirect('extraction_nac')
    else:
        form = SignUpForm()
        return render(request, 'register.html', {'form': form})

    return render(request, 'register.html', {'form': form})


def temporaire_drh(request):

    # Récupérer tous les enregistrements
    tmp_records = TemporaireDRH.objects.all()

    # Pagination
    paginator = Paginator(tmp_records, 100)  # 10 enregistrements par page
    page_number = request.GET.get('page')
    try:
        tmp_records = paginator.page(page_number)
    except PageNotAnInteger:
        # Si le numéro de page n'est pas un entier, afficher la première page
        tmp_records = paginator.page(1)
    except EmptyPage:
        # Si la page est vide, afficher la dernière page
        tmp_records = paginator.page(paginator.num_pages)

    # Mettre en forme les enregistrements pour les inclure dans le contexte
    tmp_all_records = []
    for tmp_record in tmp_records:
      tmp_all_records.append({
        'id':tmp_record.id,
        'matrh': tmp_record.matrh,
        'logon_name': tmp_record.logon_name,
        'nom': tmp_record.nom,
        'prenom': tmp_record.prenom,
        'datefin': tmp_record.datefin.strftime('%Y-%m-%d'),
        'manager': tmp_record.manager,
        'hierarchie': tmp_record.hierarchie,
    })

    context = {
        'tmp_all_records': tmp_all_records,
    }
    

    # Rendre la page d'accueil avec le contexte et les enregistrements paginés
    return render(request, 'TemporaireDRH.html', {**context, 'tmp_records': tmp_records})


def inserer_data_tmp_drh(request, donnees_csv):
    try:
        # Afficher les colonnes du DataFrame pour vérifier les noms
        print("Colonnes du DataFrame :", donnees_csv.columns.tolist())
        
        # Vérifier les colonnes du DataFrame
        expected_columns = ['matrh', 'logon_name', 'nom', 'prenom', 'datefin', 'manager', 'hierarchie']
        for column in expected_columns:
            if column not in donnees_csv.columns:
                raise ValueError(f"Colonne manquante: {column}")

        for index, row in donnees_csv.iterrows():
            # Vérifier les clés dans chaque ligne
            row = {k.lower(): v for k, v in row.items()}
            for column in expected_columns:
                if column not in row:
                    raise ValueError(f"Valeur manquante pour la colonne: {column} dans la ligne {index}")
            
            # Parse et formater la date en dd/mm/yy, puis la convertir en YYYY-MM-DD
            datefin = parser.parse(row['datefin'], dayfirst=True).date()
            formatted_date = datefin.isoformat()  # Obtenir la date au format YYYY-MM-DD

            try:
                # Insérer les données de base
                temporaire = TemporaireDRH.objects.create(
                    matrh=row['matrh'], 
                    logon_name=row['logon_name'],
                    nom=row['nom'], 
                    prenom=row['prenom'],
                    datefin=formatted_date, 
                    manager=row['manager'],
                    hierarchie=row['hierarchie'], 
                    created_at=timezone.now()
                )
                temporaire.save()
            except IntegrityError as e:
                if 'UNIQUE constraint' in str(e):  # Erreur de duplication
                    # Récupérer la dernière entrée pour le matricule RH
                    last_entry = TemporaireDRH.objects.filter(matrh=row['matrh']).order_by('-id').first()
                    if last_entry:
                        # Mettre à jour la dernière entrée avec les nouvelles données
                        last_entry.logon_name = row['logon_name']
                        last_entry.nom = row['nom']
                        last_entry.prenom = row['prenom']
                        last_entry.datefin = formatted_date  # Utiliser la date formatée
                        last_entry.manager = row['manager']
                        last_entry.hierarchie = row['hierarchie']
                        last_entry.created_at = timezone.now()
                        last_entry.save()
                        print(f"L'entrée avec le même matricule RH a été mise à jour pour l'index {index}.")
                    else:
                        print(f"Aucune entrée trouvée pour matrh {row['matrh']} lors de la mise à jour.")
                else:
                    raise  # Renvoyer l'erreur si ce n'est pas une erreur de duplication
        print("Données insérées avec succès.")
    except Exception as e:
        print("Erreur lors de l'insertion des données :", e)
        
def insert_tmp_drh(request):
    if request.method == 'POST' and request.FILES.get('file'):
        form = Upload(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            # Vérifier si le fichier est un fichier Excel ou CSV
            if file.name.endswith('.xls') or file.name.endswith('.xlsx'):
                try:
                    # Utiliser pandas pour lire les données du fichier Excel
                    donnees = pd.read_excel(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier Excel : {}".format(e))
            elif file.name.endswith('.csv'):
                try:
                    # Utiliser pandas pour lire les données du fichier CSV
                    donnees = pd.read_csv(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier CSV : {}".format(e))
            else:
                return HttpResponse("Le fichier doit être au format Excel ou CSV.")
            
            # Connexion à la base de données MySQL
            try:

                connection = connect_to_database()

                if connection.is_connected():
                    print("Connexion à la base de données MySQL réussie.")
                    inserer_data_tmp_drh(connection, donnees)
                    connection.close()
                    print("Connexion à la base de données MySQL fermée.")
            except mysql.connector.Error as e:
                print("Erreur lors de la connexion à la base de données MySQL :", e)
                return HttpResponse("Erreur lors de la connexion à la base de données MySQL")
            except Exception as e:
                print("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL :", e)
                return HttpResponse("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL")
            return redirect('temporaire_drh')
    else:
        form = Upload()
    return render(request, 'adtemporairefile.html', {'form': form})


def supprimer_tmp_data(request):
    # Supprimer toutes les données de votre modèle
    TemporaireDRH.objects.all().delete()

    return redirect('temporaire_drh')


def supprimer_ad_data(request):
    # Supprimer toutes les données de votre modèle
    AdMPReport.objects.all().delete()

    return redirect('adfile')

def supprimer_crbt_data(request):
    # Supprimer toutes les données de votre modèle
    CRBT.objects.all().delete()

    return redirect('crbtfile')


def inserer_admp_data(connection, donnees):
    cursor = connection.cursor()
    try:
        for index, row in donnees.iterrows():

            row = row.where(pd.notnull(row), None)
            row = {k.lower(): v for k, v in row.items()}
            first_name = row.get('first_name')
            last_name = row.get('last_name')
            full_name = row.get('full_name')
            display_name = row.get('display_name')
            sam_account_name = row.get('sam_account_name')
            email_address = row.get('email_address')
            account_status = row.get('account_status')
            initials = row.get('initials')
            
            # Vérifier si les valeurs de username et status sont présentes et valides
            if sam_account_name and account_status.lower() == 'enabled':
                # Insérer les données de base
                cursor.execute("INSERT INTO core_admpreport (created_at, first_name, last_name, full_name,display_name,sam_account_name, email_address,account_status, initials) VALUES (%s,%s ,%s, %s,%s,%s ,%s, %s, %s)",
                               (timezone.now(), first_name, last_name, full_name,display_name,sam_account_name, email_address,account_status, initials))
        
        # Commit après toutes les opérations
        connection.commit()
        print("Données insérées avec succès.")
    except mysql.connector.Error as e:
        print("Erreur lors de l'insertion des données :", e)
        connection.rollback()
    finally:
        cursor.close()


def insert_admp(request):
    if request.method == 'POST' and request.FILES.get('file'):
        form = Upload(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            # Vérifier si le fichier est un fichier Excel ou CSV
            if file.name.endswith('.xls') or file.name.endswith('.xlsx'):
                try:
                    # Utiliser pandas pour lire les données du fichier Excel
                    donnees = pd.read_excel(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier Excel : {}".format(e))
            elif file.name.endswith('.csv'):
                try:
                    # Utiliser pandas pour lire les données du fichier CSV
                    donnees = pd.read_csv(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier CSV : {}".format(e))
            else:
                return HttpResponse("Le fichier doit être au format Excel ou CSV.")
            
            # Connexion à la base de données MySQL
            try:

                connection = connect_to_database()

                if connection.is_connected():
                    print("Connexion à la base de données MySQL réussie.")
                    inserer_admp_data(connection, donnees)
                    connection.close()
                    print("Connexion à la base de données MySQL fermée.")
            except mysql.connector.Error as e:
                print("Erreur lors de la connexion à la base de données MySQL :", e)
                return HttpResponse("Erreur lors de la connexion à la base de données MySQL")
            except Exception as e:
                print("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL :", e)
                return HttpResponse("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL")
            
            return redirect('adfile')
    else:
        form = Upload()
    return redirect('adfile')


def adfile(request):
  # Récupérer tous les enregistrements
    ad_records =AdMPReport.objects.all()

    # Pagination
    paginator = Paginator(ad_records, 100)  # 10 enregistrements par page
    page_number = request.GET.get('page')
    try:
        ad_records = paginator.page(page_number)
    except PageNotAnInteger:
        # Si le numéro de page n'est pas un entier, afficher la première page
        ad_records = paginator.page(1)
    except EmptyPage:
        # Si la page est vide, afficher la dernière page
        ad_records = paginator.page(paginator.num_pages)

    # Mettre en forme les enregistrements pour les inclure dans le contexte
    all_ad_records = []
    for ad_record in ad_records:
        all_ad_records.append({
            'id': ad_record.id,
            'first_name': ad_record.first_name,
            'last_name': ad_record.last_name,
            'full_name': ad_record.full_name,
            'display_name': ad_record.display_name,
            'sam_account_name': ad_record.sam_account_name,
            'email_address': ad_record.email_address,
            'account_status': ad_record.account_status,
            'initials': ad_record.initials,
        })

    context = {
        'all_ad_records': all_ad_records,
    }
    

    # Rendre la page d'accueil avec le contexte et les enregistrements paginés
    return render(request, 'adfile.html', {**context, 'ad_records': ad_records})

def crbtfile(request):
  # Récupérer tous les enregistrements
    crbt_records =CRBT.objects.all()

    # Pagination
    paginator = Paginator(crbt_records, 100)  # 10 enregistrements par page
    page_number = request.GET.get('page')
    try:
        crbt_records = paginator.page(page_number)
    except PageNotAnInteger:
        # Si le numéro de page n'est pas un entier, afficher la première page
        crbt_records = paginator.page(1)
    except EmptyPage:
        # Si la page est vide, afficher la dernière page
        crbt_records = paginator.page(paginator.num_pages)

    # Mettre en forme les enregistrements pour les inclure dans le contexte
    all_crbt_records = []
    for crbt_record in crbt_records:
        all_crbt_records.append({
            'id': crbt_record.id,
            'user_name': crbt_record.user_name,
            'role_id': crbt_record.role_id,
            'user_type': crbt_record.user_type,
            'email_id': crbt_record.email_id,
        })

    context = {
        'all_crbt_records': all_crbt_records,
    }
    

    # Rendre la page d'accueil avec le contexte et les enregistrements paginés
    return render(request, 'crbtfile.html', {**context, 'crbt_records': crbt_records})


def inserer_crbt_data(connection, donnees):
    cursor = connection.cursor()
    try:
        for index, row in donnees.iterrows():

            row = row.where(pd.notnull(row), None)
            user_name = row.get('user_name')
            role_id = row.get('role_id')
            user_type = row.get('user_type')
            email_id = row.get('email_id')

            
            # Vérifier si les valeurs de username et status sont présentes et valides
            if user_name:
                # Insérer les données de base
                cursor.execute("INSERT INTO core_crbtreport (created_at, user_name, role_id, user_type, email_id) VALUES (%s,%s ,%s, %s,%s)",
                               (timezone.now(), user_name, role_id, user_type,email_id))
        
        # Commit après toutes les opérations
        connection.commit()
        print("Données insérées avec succès.")
    except mysql.connector.Error as e:
        print("Erreur lors de l'insertion des données :", e)
        connection.rollback()
    finally:
        cursor.close()


def insert_crbt(request):
    if request.method == 'POST' and request.FILES.get('file'):
        form = Upload(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            # Vérifier si le fichier est un fichier Excel ou CSV
            if file.name.endswith('.xls') or file.name.endswith('.xlsx'):
                try:
                    # Utiliser pandas pour lire les données du fichier Excel
                    donnees = pd.read_excel(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier Excel : {}".format(e))
            elif file.name.endswith('.csv'):
                try:
                    # Utiliser pandas pour lire les données du fichier CSV
                    donnees = pd.read_csv(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier CSV : {}".format(e))
            else:
                return HttpResponse("Le fichier doit être au format Excel ou CSV.")
            
            # Connexion à la base de données MySQL
            try:

                connection = connect_to_database()

                if connection.is_connected():
                    print("Connexion à la base de données MySQL réussie.")
                    inserer_crbt_data(connection, donnees)
                    connection.close()
                    print("Connexion à la base de données MySQL fermée.")
            except mysql.connector.Error as e:
                print("Erreur lors de la connexion à la base de données MySQL :", e)
                return HttpResponse("Erreur lors de la connexion à la base de données MySQL")
            except Exception as e:
                print("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL :", e)
                return HttpResponse("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL")
            
            return redirect('crbtfile')
    else:
        form = Upload()
    return redirect('crbtfile')

def export_gnoc(request, model_name, model_fields, custom_sql=None):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="records_gnoc.csv"'

    # Récupérer le modèle spécifié à partir du nom du modèle
    model = apps.get_model(app_label='nac', model_name=model_name)


    # Obtenez la connexion à la base de données
    connection = connect_to_database()



    # Récupérer les enregistrements du modèle spécifié depuis la base de données Django
    records_django = model.objects.filter(Name__regex=r'^[a-zA-Z]{4}\d{4}$').values_list(*model_fields)

    # Récupérer les enregistrements SQL depuis la base de données externe
    with connection.cursor() as cursor:
        if custom_sql:
            cursor.execute(custom_sql)
            records_sql = cursor.fetchall()

    # Créer un ensemble pour stocker les identifiants uniques
    unique_ids = set()

    # Ajouter les enregistrements SQL à l'ensemble des identifiants
    for record_sql in records_sql:
        unique_ids.add(record_sql[0])  # On suppose que le premier élément de chaque tuple est l'identifiant

    # Ajouter les enregistrements Django à l'ensemble des identifiants
    for record_django in records_django:
        unique_ids.add(record_django[0])

    # Récupérer les enregistrements correspondant aux identifiants uniques
    records_to_write = []
    for record_id in unique_ids:
        # Recherchez d'abord dans les enregistrements SQL
        for record_sql in records_sql:
            if record_sql[0] == record_id:  # Si l'identifiant correspond
                records_to_write.append(record_sql)
                break
        else:
            # Sinon, recherchez dans les enregistrements Django
            for record_django in records_django:
                if record_django[0] == record_id:  # Si l'identifiant correspond
                    records_to_write.append(record_django)
                    break

    # Écrire les enregistrements dans le fichier CSV
    writer = csv.writer(response, delimiter=",")
    writer.writerow(model_fields)
    for record in records_to_write:
        writer.writerow(record)

    return response


def export_tmp(request, model_name, model_fields, app_label,custom_sql=None):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="records_tmp.csv"'

    # Récupérer le modèle spécifié à partir du nom du modèle
    model = apps.get_model(app_label, model_name=model_name)

    # Obtenez la connexion à la base de données
    connection = connect_to_database()

    # Récupérer les enregistrements du modèle spécifié depuis la base de données Django
    records_django = model.objects.filter(
        Q(Name__istartswith="tmp") |
        Q(Name__istartswith="ext") |
        Q(Name__istartswith="INT")
    ).exclude(commentaire__istartswith="A supprimer")

    if custom_sql:
        # Récupérer les enregistrements SQL depuis la base de données externe
        with connection.cursor() as cursor:
            cursor.execute(custom_sql)
            records_sql = cursor.fetchall()

        # Créer un ensemble pour stocker les identifiants uniques
        unique_ids = set()

        # Ajouter les enregistrements SQL à l'ensemble des identifiants
        for record_sql in records_sql:
            unique_ids.add(record_sql[0])  # On suppose que le premier élément de chaque tuple est l'identifiant

        # Ajouter les enregistrements Django à l'ensemble des identifiants
        for record_django in records_django:
            unique_ids.add(record_django.id)

        # Récupérer les enregistrements correspondant aux identifiants uniques
        records_to_write = []
        for record_id in unique_ids:
            # Recherchez d'abord dans les enregistrements SQL
            for record_sql in records_sql:
                if record_sql[0] == record_id:  # Si l'identifiant correspond
                    records_to_write.append(record_sql)
                    break
            else:
                # Sinon, recherchez dans les enregistrements Django
                for record_django in records_django:
                    if record_django.id == record_id:  # Si l'identifiant correspond
                        records_to_write.append(record_django)
                        break

        writer = csv.writer(response, delimiter=",")
        writer.writerow(model_fields)  # Écrire les en-têtes de colonne
        for record in records_to_write:
            # Extraire les valeurs de l'objet Extraction_nac dans une liste ou un tuple
            values = [getattr(record, field) for field in model_fields]
            writer.writerow(values)

    return response

def export_desc(request, model_name, model_fields, app_label ,search_field, regex_pattern,custom_sql=None, prefixes_to_filter=None):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="records_desc.csv"'

    model = apps.get_model(app_label, model_name=model_name)
    
    connection = connect_to_database()



    # Récupérer les enregistrements du modèle spécifié depuis la base de données Django
    # records_django = model.objects.filter(Name__regex=r'^[a-zA-Z]{4}\d{4}$').values_list(*model_fields)
    records_django = model.objects.filter(
        **{f"{search_field}__regex": regex_pattern}
    ).values_list(*model_fields)

    # Récupérer les enregistrements à supprimer depuis la base de données SQL
    with connection.cursor() as cursor:
        if custom_sql:
            cursor.execute(custom_sql)
            records_sql = cursor.fetchall()
        else:
            records_sql = []

    # Construire le filtre dynamiquement
    filters = Q()
    if prefixes_to_filter:
        for prefix in prefixes_to_filter:
            filters |= Q(username__istartswith=prefix)

    # Récupérer les enregistrements à supprimer depuis la base de données Django

    # Créer un dictionnaire pour stocker les enregistrements avec l'identifiant comme clé
    records_dict = {}

    # Ajouter les enregistrements SQL dans le dictionnaire
    for record_sql in records_sql:
        records_dict[record_sql[0]] = record_sql

    # Ajouter les enregistrements Django dans le dictionnaire en évitant les doublons
    for record_django in records_django:
        if record_django.id not in records_dict:
            # Extraire les valeurs des champs de modèle dans une liste ou un tuple
            values = [getattr(record_django, field) for field in model_fields]
            records_dict[record_django.id] = values

    # Écrire les enregistrements dans le fichier CSV
    writer = csv.writer(response, delimiter=",")
    writer.writerow(model_fields)  # Écrire les en-têtes de colonne
    for record in records_dict.values():
        writer.writerow(record)

    return response

import re

def update_from_adm(request, extraction_model, name_field, app_label):
    # Récupérer le modèle d'extraction spécifié
    ExtractionModel = apps.get_model(app_label, extraction_model)
    criteres = ["pcci", "stl", "1431", "1413", "ksv", "w2c", "pop_", "pdist", "sitel", "psup"]
    gnoc_regex = r'^[a-zA-Z]{4}\d{4}$'

    # Récupérer tous les enregistrements du modèle d'extraction spécifié
    extraction_records = ExtractionModel.objects.all()

    for extraction_record in extraction_records:
        name = getattr(extraction_record, name_field)
        highest_score = 0
        best_match = None

        # Recherche de tous les utilisateurs dans AdMPReport
        potential_matches = AdMPReport.objects.all()

        # Calcul de la similitude entre le nom et chaque nom d'utilisateur trouvé
        for ad_record in potential_matches:
            score = fuzz.ratio(name.lower(), getattr(ad_record, 'sam_account_name').lower())
            if score > highest_score:
                highest_score = score
                best_match = ad_record

        # Décision basée sur le score de similitude le plus élevé et le statut
        if best_match and highest_score >= 95:
            if best_match.account_status.lower() == 'disabled':
                commentaire = "A supprimer"
            else:
                commentaire = "A garder"
                print(best_match)
                print(highest_score)
        else:
            commentaire = "A supprimer, non présent dans l'AD"
            
        # Vérification si le nom commence par l'un des critères
        if any(name.lower().startswith(critere) for critere in criteres):
            commentaire = "Fiabilisation DESC"
        
        # Vérification si le nom correspond au regex GNOC
        if re.match(gnoc_regex, name):
            commentaire = "A envoyer a GNOC"
        
        # Mise à jour de l'enregistrement avec le nouveau commentaire
        extraction_record.commentaire = commentaire
        extraction_record.save()

def update_from_temporaireDRH(extraction_model, name_field):
    # Récupérer tous les enregistrements du modèle extraction

    extraction_records = extraction_model.objects.filter(
        **{f"{name_field}__istartswith": "tmp"}
    ) | extraction_model.objects.filter(
        **{f"{name_field}__istartswith": "INT"}
    )

    # Récupérer tous les noms des enregistrements du modèle TemporaireDRH
    temporaire_records = TemporaireDRH.objects.values_list('logon_name', flat=True)

    # Parcourir chaque enregistrement de extraction_records
    for extraction_record in extraction_records:
        Name = getattr(extraction_record, name_field)
        commentaire = ""

        # Rechercher une correspondance partielle dans les noms des enregistrements TemporaireDRH avec un score supérieur ou égal à 80%
        match = process.extractOne(Name, temporaire_records, scorer=fuzz.partial_ratio, score_cutoff=100)

        if match:
            # Obtenez l'objet TemporaireDRH correspondant
            temporaire_record = TemporaireDRH.objects.get(logon_name=match[0])
            datefin = temporaire_record.datefin

            # Vérifier si la date de fin du contrat est dépassée
            if datefin < date.today():
                commentaire = "Fin de contrat, à supprimer"
            else:
                commentaire = 'A garder'
        else:
            # Aucune correspondance trouvée
            commentaire = 'A supprimer, non present dans la liste DRH'

        # Mettre à jour le commentaire dans l'enregistrement extraction
        extraction_record.commentaire = commentaire  
        extraction_record.save()


def export_all(request, model_name, model_fields, app_label, custom_sql=None):
    # Créer une réponse HTTP avec le type de contenu CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Fiable.csv"'

    # Récupérer le modèle spécifié à partir du nom du modèle
    model = apps.get_model(app_label, model_name=model_name)

    # Récupérer les enregistrements du modèle spécifié depuis la base de données Django
    records_django = model.objects.all()

    # Si une requête SQL personnalisée est fournie, exécutez-la pour récupérer les enregistrements
    if custom_sql:
        with connection.cursor() as cursor:
            cursor.execute(custom_sql)
            records_sql = cursor.fetchall()
    else:
        records_sql = []

    # Créer une liste pour stocker tous les enregistrements à écrire dans le fichier CSV
    records_to_write = []

    # Ajouter les enregistrements Django à la liste des enregistrements à écrire
    for record_django in records_django:
        records_to_write.append(record_django)

    # Ajouter les enregistrements SQL à la liste des enregistrements à écrire
    for record_sql in records_sql:
        records_to_write.append(record_sql)

    # Écrire les données dans le fichier CSV
    writer = csv.writer(response, delimiter=",")
    writer.writerow(model_fields)  # Écrire les en-têtes de colonne

    for record in records_to_write:
        if isinstance(record, model):
            # Si c'est une instance de modèle Django, extraire les valeurs des champs
            values = [getattr(record, field) for field in model_fields]
        else:
            # Sinon, c'est un tuple, utilisez-le directement
            values = record
        writer.writerow(values)

    return response

#User Pretups 

def user_pretups(request):
    # Récupérer tous les enregistrements
    user_pretups_records = Extraction_user_pretups.objects.all()

    # Pagination
    paginator = Paginator(user_pretups_records, 100)  # 100 enregistrements par page
    page_number = request.GET.get('page')
    try:
        user_pretups_records = paginator.page(page_number)
    except PageNotAnInteger:
        # Si le numéro de page n'est pas un entier, afficher la première page
        user_pretups_records = paginator.page(1)
    except EmptyPage:
        # Si la page est vide, afficher la dernière page
        user_pretups_records = paginator.page(paginator.num_pages)

    # Mettre en forme les enregistrements pour les inclure dans le contexte
    all_user_pretups_records = []
    for user_pretups_record in user_pretups_records:
        all_user_pretups_records.append({
            'id': user_pretups_record.id,
            'login_id': user_pretups_record.login_id,
            'traitement_fiabilisation': user_pretups_record.traitement_fiabilisation,
        })

    context = {
        'all_user_pretups_records': all_user_pretups_records,
    }

    # Rendre la page d'accueil avec le contexte et les enregistrements paginés
    return render(request, 'user_pretups.html', {**context, 'user_pretups_records': user_pretups_records})

def inserer_user_pretups_data(connection, donnees):
    cursor = connection.cursor()
    try:
        for index, row in donnees.iterrows():
            # Conversion des clés en minuscules et gestion des valeurs nulles
            row = {k.lower(): v for k, v in row.items()}
            row = {k: v if pd.notnull(v) else None for k, v in row.items()}

            # Extraction des valeurs des colonnes

            login_id = row.get('login_id')
            traitement_fiabilisation = row.get('traitement_fiabilisation')

            # # Conversion des dates si nécessaire
            # if isinstance(last_login_on, str):
            #     last_login_on = parser.parse(last_login_on)

            # if isinstance(pswd_modified, str):
            #     pswd_modified = parser.parse(pswd_modified)

            # if isinstance(created_on, str):
            #     created_on = parser.parse(created_on)

            # if isinstance(modified_on, str):
            #     modified_on = parser.parse(modified_on)

            # Insérer les données dans la base de données
            cursor.execute(
                """
                INSERT INTO core_extraction_user_pretups (
                    login_id, traitement_fiabilisation
                ) VALUES (%s, %s)
                """,
                (login_id, traitement_fiabilisation)
            )
        
        # Commit après toutes les opérations
        connection.commit()
        print("Données insérées avec succès.")
    except mysql.connector.Error as e:
        print("Erreur lors de l'insertion des données :", e)
        connection.rollback()
    finally:
        cursor.close()

def insert_user_pretups(request):
    if request.method == 'POST' and request.FILES.get('file'):
        form = Upload(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            # Vérifier si le fichier est un fichier Excel ou CSV
            if file.name.endswith('.xls') or file.name.endswith('.xlsx'):
                try:
                    # Utiliser pandas pour lire les données du fichier Excel
                    donnees = pd.read_excel(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier Excel : {}".format(e))
            elif file.name.endswith('.csv'):
                try:
                    # Utiliser pandas pour lire les données du fichier CSV
                    donnees = pd.read_csv(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier CSV : {}".format(e))
            else:
                return HttpResponse("Le fichier doit être au format Excel ou CSV.")
            
            # Connexion à la base de données MySQL
            try:
                connection = connect_to_database()

                if connection.is_connected():
                    print("Connexion à la base de données MySQL réussie.")
                    inserer_user_pretups_data(connection, donnees)
                    connection.close()
                    print("Connexion à la base de données MySQL fermée.")
            except mysql.connector.Error as e:
                print("Erreur lors de la connexion à la base de données MySQL :", e)
                return HttpResponse("Erreur lors de la connexion à la base de données MySQL")
            except Exception as e:
                print("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL :", e)
                return HttpResponse("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL")
            
            return redirect('user_pretups')
    else:
        form = Upload()
    return redirect('user_pretups')



def supprimer_user_pretups_data(request):
    # Supprimer toutes les données de votre modèle
    Extraction_user_pretups.objects.all().delete()

    return redirect('user_pretups')

def export_user_pretups_fiable(request):
    model_fields = [ 'login_id', 'traitement_fiabilisation']

    model_name='Extraction_user_pretups'

    response=export_all(request, model_name=model_name, model_fields=model_fields,app_label='core')
    
    return response


def update_from_user_pretups(extraction_model, name_field):
    # Récupérer tous les enregistrements de extraction_model
    extraction_records = extraction_model.objects.all()

    # Récupérer tous les login_id des enregistrements de Extraction_user_pretups
    temporaire_records = Extraction_user_pretups.objects.values_list('login_id', flat=True)

    # Parcourir chaque enregistrement de extraction_records
    for extraction_record in extraction_records:
        name = getattr(extraction_record, name_field)
        traitement_fiabilisation = ""

        # Vérifier s'il y a une correspondance dans temporaire_records
        if name in temporaire_records:
            # Si une correspondance est trouvée, récupérer tous les enregistrements correspondants dans Extraction_user_pretups
            matching_records = Extraction_user_pretups.objects.filter(login_id=name)
            # Parcourir chaque enregistrement correspondant et les mettre à jour
            for temporaire_record in matching_records:
                temporaire_record.traitement_fiabilisation = "Alerte"
                temporaire_record.save()
                traitement_fiabilisation = temporaire_record.traitement_fiabilisation

        # Mettre à jour le champ traitement_fiabilisation dans l'enregistrement extraction
        extraction_record.traitement_fiabilisation = traitement_fiabilisation
        extraction_record.save()




def update_test_user_pretups(request):
    update_from_user_pretups(Compte_users_deleted,"login_id")


    return redirect("user_pretups")


def user_deleted(request):
    # Récupérer tous les enregistrements
    users = Compte_users_deleted.objects.all()

    # Pagination
    paginator = Paginator(users, 100)  # 100 enregistrements par page
    page_number = request.GET.get('page')
    try:
        users = paginator.page(page_number)
    except PageNotAnInteger:
        # Si le numéro de page n'est pas un entier, afficher la première page
        users = paginator.page(1)
    except EmptyPage:
        # Si la page est vide, afficher la dernière page
        users = paginator.page(paginator.num_pages)

    # Mettre en forme les enregistrements pour les inclure dans le contexte
    all_users = []
    for user in users:
        all_users.append({
            'id': user.id,
            'login_id': user.login_id,
        })

    context = {
        'all_users': all_users,
    }

    # Rendre la page d'accueil avec le contexte et les enregistrements paginés
    return redirect('user_pretups')

def inserer_user_data(connection, donnees):
    cursor = connection.cursor()
    try:
        for index, row in donnees.iterrows():
            # Conversion des clés en minuscules et gestion des valeurs nulles
            row = {k.lower(): v for k, v in row.items()}
            row = {k: v if pd.notnull(v) else None for k, v in row.items()}

            # Extraction des valeurs des colonnes
            login_id = row.get('login_id')


            cursor.execute(
                """
                INSERT INTO core_compte_users_deleted (
                    login_id
                ) VALUES (%s)
                """,
                (login_id, )
            )
        
        # Commit après toutes les opérations
        connection.commit()
        print("Données insérées avec succès.")
    except mysql.connector.Error as e:
        print("Erreur lors de l'insertion des données :", e)
        connection.rollback()
    finally:
        cursor.close()

def insert_user_deleted(request):
    if request.method == 'POST' and request.FILES.get('file'):
        form = Upload(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            # Vérifier si le fichier est un fichier Excel ou CSV
            if file.name.endswith('.xls') or file.name.endswith('.xlsx'):
                try:
                    # Utiliser pandas pour lire les données du fichier Excel
                    donnees = pd.read_excel(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier Excel : {}".format(e))
            elif file.name.endswith('.csv'):
                try:
                    # Utiliser pandas pour lire les données du fichier CSV
                    donnees = pd.read_csv(file)
                except Exception as e:
                    return HttpResponse("Erreur lors de la lecture du fichier CSV : {}".format(e))
            else:
                return HttpResponse("Le fichier doit être au format Excel ou CSV.")
            
            # Connexion à la base de données MySQL
            try:
                connection = connect_to_database()

                if connection.is_connected():
                    print("Connexion à la base de données MySQL réussie.")
                    inserer_user_data(connection, donnees)
                    connection.close()
                    print("Connexion à la base de données MySQL fermée.")
            except mysql.connector.Error as e:
                print("Erreur lors de la connexion à la base de données MySQL :", e)
                return HttpResponse("Erreur lors de la connexion à la base de données MySQL")
            except Exception as e:
                print("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL :", e)
                return HttpResponse("Une erreur s'est produite lors de l'insertion des données dans la base de données MySQL")
            
            return redirect('user_deleted')
    else:
        form = Upload()
    return redirect('user_deleted')



def supprimer_user_data(request):
    # Supprimer toutes les données de votre modèle
    Compte_users_deleted.objects.all().delete()

    return redirect('user_pretups')