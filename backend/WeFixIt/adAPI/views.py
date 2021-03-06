import datetime
from django.http import HttpResponse, HttpResponseNotFound
from django.template import loader
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from .ad_data import create_and_save_data, select_ad_by_click_rate
from .models import Campaign, Advertisement
from .serializers import CampaignSerializer, AdvertisementSerializer
from django.http import JsonResponse
import csv


class AdvertisementList(generics.ListCreateAPIView):
    permission_classes = (IsAdminUser,)
    """
    Class that contains all the advertisements in our database
    """
    queryset = Advertisement.objects.all().order_by('id')
    serializer_class = AdvertisementSerializer


class AdvertisementDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminUser,)
    """
    Class that allows you to create, update, or destroy advertisements
    in the database
    """
    queryset = Advertisement.objects.all().order_by('id')
    serializer_class = AdvertisementSerializer


class CampaignList(generics.ListCreateAPIView):
    permission_classes = (IsAdminUser,)
    """
    Class that contains all the campaigns in our database
    """
    queryset = Campaign.objects.all().order_by('name')
    serializer_class = CampaignSerializer


class CampaignDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsAdminUser,)
    """
    Class that allows you to create, update, or destroy campaigns in the
    database
    """
    queryset = Campaign.objects.all().order_by('name')
    serializer_class = CampaignSerializer


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_home_view(request):
    """
    Returns an HTML response containing the HTML for the home page.

    Args:
        request: a GET request. User must be Admin to access.
    Return:
        HTML response of the home page data.
    """
    template = loader.get_template('adAPI/home.html')
    return HttpResponse(template.render())


@api_view(['GET'])
@permission_classes([AllowAny])
def get_ad(request):
    """
    Function that randomly returns a single ad in the database.
    """
    print(request.query_params)
    campaigns = Campaign.objects.filter(start_date__lte=datetime.date.today())\
        .filter(end_date__gte=datetime.date.today())

    if 'country' in request.query_params.keys():
        if request.query_params['country']:
            campaigns = campaigns.filter(countries__contains=request.
                                         query_params['country'])

    print("Campaigns: ", end="")
    print(campaigns)
    ad_ids = set()
    for campaign in campaigns:
        ad_query = Campaign.objects.filter(id=campaign.id) \
                           .values_list('advertisements', flat=True)
        print(ad_query)
        ad_query_set = set(ad_query)
        print(ad_query_set)
        ad_query_set.discard(None)
        print(ad_query_set)
        ad_ids.update(set(ad_query_set))

    print("Possible ad ids: " + str(ad_ids))
    advertisement = select_ad_by_click_rate(Advertisement.
                                            objects.filter(pk__in=ad_ids))

    if not advertisement:
        return JsonResponse({"detail": "not found"})
    print("Printing advertisement")
    print(advertisement)
    serializer = AdvertisementSerializer(advertisement)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def click_ad(request, ad_id):
    """
    Update the database to show a user clicked on the ad with a given id.
    This function is not idempotent, and repeated requests will result in
    different values.

    Args:
        request: the HttpRequest given by the user from the URL
        ad_id: Id of the ad clicked on.
    Return:
        An HttpResponse indicating success/failure of POST request.
        Request fails only if ad with id=id not present.
    """
    try:
        ad_object = Advertisement.objects.get(id=ad_id)
        ad_object.clicks += 1
        ad_object.save()
        msg = f'Advertisement {ad_id} updated.'
        return HttpResponse(msg, content_type='text/plain')
    except Advertisement.DoesNotExist:
        return HttpResponseNotFound()


@api_view(['POST'])
@permission_classes([AllowAny])
def view_ad(request, ad_id):
    """
    Update the database to show a user viewed an ad with a given id.

    This function is not idempotent, and repeated requests will result in
    different values.

    Args:
        request: the HttpRequest given by the user from the URL
        ad_id: Id of the ad clicked on.
    Return:
        An HttpResponse indicating success/failure of POST request.
        Request fails only if ad with id=id not present.
    """
    try:
        ad_object = Advertisement.objects.get(id=ad_id)
        ad_object.views += 1
        ad_object.save()
        msg = f'Advertisement {ad_id} updated.'
        return HttpResponse(msg, content_type='text/plain')
    except Advertisement.DoesNotExist:
        # ad is not found in the database, an error response should be returned
        return HttpResponseNotFound()


@api_view(['GET'])
@permission_classes([AllowAny])
def get_performance(request):
    """
    Generates a visual representing the performance of each ad in terms of
    clicks and views, and returns an html response with the visual within
    the template.

    Most browsers cache static data files, so if the file is not updating, you
    need to hard refresh your browser with Ctrl-Shift-R

    Args:
        request: An HttpRequest that must be a GET request
    Return:
        HttpResponse containing a template containing the performance image.
    """
    create_and_save_data()
    template = loader.get_template('adAPI/performance.html')
    return HttpResponse(template.render())


@api_view(['GET'])
def get_csv(request):
    """
    Generates a CSV of analytics data containing the header text,
    number of clicks, and number of views.

    Uses the CSV writer because the HTTPResponse is a file-like object.
    """
    all_records = Advertisement.objects.all()\
        .values_list('header_text', 'clicks', 'views')
    response = HttpResponse(content_type='text/csv')

    csv_writer = csv.writer(response)
    csv_writer.writerow(['Header Text', 'Clicks', 'Views'])

    for record in all_records:
        csv_writer.writerow(record)

    response['Content-Disposition'] = 'attachment; filename="analytics.csv"'

    return response


@api_view(['Delete'])
@permission_classes([IsAdminUser])
def nuke(request, format=None):
    campaigns = Campaign.objects.all()
    advertisements = Advertisement.objects.all()
    deleted_campaigns_list = []
    deleted_ad_list = []

    for campaign in campaigns:
        serializer = CampaignSerializer(campaign)

        campaign_name = serializer.data['name']
        deleted_campaigns_list.append(campaign_name)

    for ad in advertisements:
        serializer = AdvertisementSerializer(ad)

        ad_id = serializer.data['id']
        deleted_ad_list.append(ad_id)

    content = {
        'status': 'requested allowed... nuked',
        'deletedCampaigns': deleted_campaigns_list,
        'deletedAdvertisements': deleted_ad_list
    }

    campaigns.delete()
    advertisements.delete()

    return Response(content)
