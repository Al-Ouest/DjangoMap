from django.db import models
from django.utils.text import slugify
from django_markdown.models import MarkdownField
import itertools
import os
from geopy.geocoders import GoogleV3
from django_mailbox.signals import message_received
from django.dispatch import receiver
from datetime import datetime
from destination_australia import settings


@receiver(message_received)
def create_milestone(sender, message, **args):
    print(message.from_address)
    if message.from_address[0] in settings.VERIFIED_TRAVELLERS:
        print("Verified traveller, now creating milestone.")
        milestone = Milestone()
        if message.attachments.all():
            print("There is attachment(s) to this mail.")
            for attachment in message.attachments.all():
                # TODO Ca ne fonctionne pas putain de bordel de merde
                print(attachment.document)
                milestone.photos.add(attachment.document)
        milestone.title = message.subject
        milestone.arrival_date = datetime.now()
        milestone.text = message.text
        milestone.save()


# This manager exclude draft milestones
class CompletedMilestoneManager(models.Manager):
    def get_queryset(self):
        return super(CompletedMilestoneManager, self).get_queryset().exclude(draft=True)


class Milestone(models.Model):
    title = models.CharField(max_length=100, verbose_name="titre")
    latitude = models.FloatField(editable=False)
    longitude = models.FloatField(editable=False)
    arrival_date = models.DateTimeField(verbose_name="date d'arrivée")
    text = MarkdownField(verbose_name="texte")
    draft = models.BooleanField('Brouillon ?', default=False, help_text="Les brouillons ne seront pas publiés.")

    slug = models.SlugField(max_length=100, unique=True, editable=False)

    # This is the default manager, we keep this one for the admin
    objects = models.Manager()
    # We use our custom manager to display only completed milestones on the website
    completed_objects = CompletedMilestoneManager()

    def get_absolute_url(self):
        return ''

    class Meta:
        verbose_name = "étape"
        verbose_name_plural = "étapes"

    def save(self, *args, **kwargs):
        self.slug = orig = slugify(self.title)
        for x in itertools.count(1):
            if not Milestone.objects.filter(slug=self.slug).exists():
                break
            self.slug = '%s-%d' % (orig, x)
        geolocator = GoogleV3()
        location = geolocator.geocode(self.title)
        self.latitude = location.latitude
        self.longitude = location.longitude
        if hasattr(self, 'video'):
            self.video = self.video.replace('watch?v=', 'embed/')
        super(Milestone, self).save(*args, **kwargs)

    def __str__(self):
        return self.title


class Comment(models.Model):
    alias = models.CharField(max_length=25)
    content = models.TextField(verbose_name="contenu")
    pub_date = models.DateTimeField(auto_now_add=True, verbose_name="date de publication")
    milestone = models.ForeignKey(Milestone, related_name='comments', verbose_name="étapes")
    photo = models.ImageField(upload_to='photos/comments/', blank=True)

    class Meta:
        verbose_name = "commentaire"
        verbose_name_plural = "commentaires"

    def __str__(self):
        return self.alias


class Photo(models.Model):
    photo = models.ImageField(upload_to='photos/milestone/')
    legend = models.TextField(verbose_name="legend", blank=True)
    milestone = models.ForeignKey(Milestone, related_name='photos', verbose_name="étapes")

    def __str__(self):
        return self.milestone.title


class Video(models.Model):
    video = models.URLField(blank=True)
    legend = models.TextField(verbose_name="legend", blank=True)
    milestone = models.ForeignKey(Milestone, related_name='videos', verbose_name="étapes")

    def save(self, *args, **kwargs):
        self.video = self.video.replace('watch?v=', 'embed/')
        super(Video, self).save(*args, **kwargs)
