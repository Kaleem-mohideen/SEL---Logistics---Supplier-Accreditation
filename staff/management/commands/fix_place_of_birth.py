from django.core.management.base import BaseCommand
from staff.models import StaffMember


class Command(BaseCommand):
    help = "Populate place_of_birth with country code for non-Italy records"

    def handle(self, *args, **options):

        qs = StaffMember.objects.filter(
            place_or_city_of_birth__isnull=True,
            country_of_birth__isnull=False
        ).exclude(country_of_birth__code="ITA")

        updated = 0

        for s in qs:
            s.place_of_birth_country_code = s.country_of_birth.code
            s.save(update_fields=["place_of_birth_country_code"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Updated {updated} staff records.")
        )
