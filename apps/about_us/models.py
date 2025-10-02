from django.db import models
from django.core.exceptions import ValidationError

class ContactInfo(models.Model):
    support_phone = models.CharField(
        max_length=30,
        verbose_name="Support Phone",
        help_text="Enter the support phone number"
    )
    email = models.EmailField(
        verbose_name="Support Email",
        help_text="Enter support contact email"
    )
    address = models.TextField(
        verbose_name="Address",
        help_text="Enter your office or company address"
    )
    telegram = models.URLField(blank=True, null=True, verbose_name="Telegram URL")
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram URL")
    twitter = models.URLField(blank=True, null=True, verbose_name="Twitter URL")
    linkedin = models.URLField(blank=True, null=True, verbose_name="LinkedIn URL")
    youtube = models.URLField(blank=True, null=True, verbose_name="YouTube URL")
    about_us = models.TextField(
        blank=True,
        null=True,
        verbose_name="About Us Text",
        help_text="Write a description about your company or platform"
    )

    class Meta:
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"

    def __str__(self):
        return "Contact Information"

