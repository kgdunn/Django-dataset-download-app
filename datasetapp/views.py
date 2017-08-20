"""
:copyright: Copyright 2010, by Kevin Dunn
:license: BSD, see LICENSE file for details.

Future enhancements
-------------------
Return better 404's
Show the first 10 rows and K columns on the dataset
Links to go the next and previous datasets

"""
# Standard library imports
import os, logging.handlers

# Other imports
from ipware.ip import get_real_ip

# Django imports
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic.list import ListView
from django.views.generic.base import TemplateView
from django.core.urlresolvers import reverse as django_reverse
from django.shortcuts import render

# Pulls in some standard entries for the template context; please see
# http://www.djangoproject.com/documentation/settings/#template-context-processors
from django.template import RequestContext, loader

# Model imports
from .models import DataFile, Dataset, Hit, Tag

# Logging code
# ---------------------
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOG_FILE_NAME = parent_dir + os.sep + 'logfile.log'
log_file = logging.getLogger('datasetapp')
log_file.setLevel(logging.DEBUG)
fh = logging.handlers.RotatingFileHandler(LOG_FILE_NAME,
                                          maxBytes=5000000,
                                          backupCount=10)
formatter = logging.Formatter(('%(asctime)s - %(name)s '
                               '- %(levelname)s - %(message)s'))
fh.setFormatter(formatter)
log_file.addHandler(fh)


def get_IP_address(request):
    """
    Returns the visitor's IP address as a string.
    """
    # Catchs the case when the user is on a proxy
    try:
        ip = request.META['HTTP_X_FORWARDED_FOR']
    except KeyError:
        ip = ''
    else:
        # HTTP_X_FORWARDED_FOR is a comma-separated list; take first IP:
        ip = ip.split(',')[0]

    if ip == '' or ip.lower() == 'unkown':
        ip = request.META['REMOTE_ADDR']      # User is not on a proxy
    return ip

def display_by_tag(request, tag):
    """
    Shows only the datasets with the given tag
    """
    log_file.debug('Tag view for tag=%s' % tag)
    dataset_list = Dataset.objects.filter(tags__name__startswith=tag)
    template = loader.get_template('all_datasets.html')

    context = {
            'dataset_list': dataset_list,
            'show_home_page': True,
            'current_tag': tag,
            'current_tag_description': Tag.objects.get(name__exact=tag).description,
        }
    return HttpResponse(template.render(context))


def display_all(request):
    """
    Displays all datasets in a table form, with brief summaries.
    """
    # django-name='dataset-home-page'
    dataset_list = Dataset.objects.order_by('slug')[:]
    template = loader.get_template('all_datasets.html')
    context = {'dataset_list': dataset_list,
               'special_message': (r'<p>You are generally free to use these '
                                'datasets in any way you like. Please '
                                'click on the dataset name to find out '
                                'more information about it.'
                                '<p>All data sets are used in the book <a href=http://learnche.org/pid>"Process Improvement using Data"</a>'),
        }
    return HttpResponse(template.render(context))


def about_dataset(request, dataset_name=None):
    """
    Displays more information about a dataset
    """
    # django-name='dataset-about-a-dataset'

    # "slug" is the unique key in the "Dataset" table
    ds = Dataset.objects.filter(slug=dataset_name.lower())
    if len(ds) == 0:
        log_file.error('An invalid dataset was requested' %
                       dataset_name.lower())
        return HttpResponseRedirect(django_reverse('dataset-home-page'))

    files = DataFile.objects.filter(dataset=ds[0])
    template = loader.get_template('dataset_info.html')
    context = {
                'ds': ds[0],
                'dfile':  files[0],
                'num_hits': Hit.objects.filter(dataset_hit=files[0]).count(),

            }
    return HttpResponse(template.render(context))


def download_dataset(request, file_name=None):
    """
    Downloads a dataset.  Wrap through a view function so that we can increment
    the hit counter.

    We arrive by: http://localhost/file/cheddar-cheese.csv
    We redirect the user to http://localhost/media/datasets/cheddar-cheese.csv
    Make sure your Apache settings are set to intercept that request before it hits Django

    """
    # django-name='dataset-download'
    file_name = file_name.lower()
    [base_name, extension] = file_name.split('.')

    # Which ``dataset`` object did this come from.  The file_name is the same
    # as the ``dataset`` object's slug (also the primary key) field.
    # Once we have the dataset, we can narrow down the file type with the
    # extension
    try:
        dataset_instance = Dataset.objects.filter(slug=base_name)[0]
    except IndexError:
        log_file.warning('File not found; user request = %s; base_name=%s' % (file_name, base_name))
        return HttpResponse('File not found', status=404)

    try:
        file_obj = DataFile.objects.filter(dataset=dataset_instance,
                                              file_type=extension.upper())[0]
    except IndexError:
        log_file.error('Data set instance exists, but file type (%s) was not '
                    'found: %s' % (extension.upper(), str(dataset_instance)))
        return HttpResponse('Not found', status=404)

    # Increment hit counter
    try:
        dataset_hit = Hit(UA_string = request.META['HTTP_USER_AGENT'],
                             IP_address = get_real_ip(request), #get_IP_address(request),
                             dataset_hit = file_obj,
                             referrer = request.META.get('HTTP_REFERER', ''))
        dataset_hit.save()
    except Exception as e:
        log_file.error('Failed to create Hit object: {0}'.format(e))

    log_file.info('Successfully downloaded file: %s' % file_name)
    log_file.info('Redirected to: %s' % file_obj.link_to_file.url)

    #response = HttpResponse(mimetype='application/' + extension.lower())
    #response['Content-Disposition'] = 'attachment; filename=%s' % file_name
    return HttpResponseRedirect('/' + file_obj.link_to_file.url)
