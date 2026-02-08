from django.db import models

class SiteSettings(models.Model):
    site_name = models.CharField(max_length=150, help_text="Name of your website or brand.")
    tagline = models.CharField(max_length=255, blank=True, null=True, help_text="Short tagline or slogan.")
    
    logo = models.ImageField(upload_to='site/logo/', blank=True, null=True)
    icon = models.ImageField(upload_to='site/icon/', blank=True, null=True, help_text="Favicon or site icon (PNG/ICO).")
    
    contact_email = models.EmailField(max_length=100, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_url = models.URLField(max_length=255, blank=True, null=True, help_text="Link to the contact page.")
    
    facebook = models.URLField(max_length=255, blank=True, null=True)
    twitter = models.URLField(max_length=255, blank=True, null=True)
    instagram = models.URLField(max_length=255, blank=True, null=True)
    linkedin = models.URLField(max_length=255, blank=True, null=True)
    youtube = models.URLField(max_length=255, blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Site Setting"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.site_name


class PromoCode(models.Model):
    PROMO_TYPE_CHOICES = [
        ('amount', 'Amount'),
        ('percentage', 'Percentage'),
    ]

    promo_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="The promo code users will enter. Example: WELCOME100"
    )

    promo_type = models.CharField(
        max_length=20,
        choices=PROMO_TYPE_CHOICES,
        default='amount',
        help_text="Select whether this promo gives a fixed amount or a percentage discount."
    )

    reward_amount = models.FloatField(
        blank=True, null=True,
        help_text="Enter the bonus amount (used when promo type = amount)."
    )

    reward_percentage = models.FloatField(
        blank=True, null=True,
        help_text="Enter the percentage value (used when promo type = percentage)."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Promo Code"
        verbose_name_plural = "Promo Codes"

    def __str__(self):
        return f"{self.promo_code}"