from django.test import TestCase

from app.models import TicketDiscount

from app.forms import TicketDiscountForm



class ticketDiscountModelTest(TestCase):
    #def setUp(self):

    def test_create_ticket_discount(self):
        """Test que verifica la creación correcta de descuentos de entradas"""
        discount = TicketDiscount.objects.create(
            percentage=10,
            code="DESCUENTO10"
        )
        self.assertIsInstance(discount, TicketDiscount)
        self.assertEqual(discount.percentage, 10)
        self.assertEqual(discount.code, "DESCUENTO10")

    def test_ticket_discount_update(self):
        """Test que verifica la actualización de descuentos de entradas mediante un formulario"""

        # Datos iniciales
        discount = TicketDiscount.objects.create(
            code="CODIGOANTIGUO1",
            percentage=15
        )

        # Nuevos datos
        new_data = {
            "code": "NUEVOCODIGO1",
            "percentage": 20
        }

        form = TicketDiscountForm(new_data, instance=discount)

        self.assertTrue(form.is_valid())
        updated_discount = form.save()

        # Verificar que los datos fueron actualizados correctamente
        self.assertEqual(updated_discount.code, "NUEVOCODIGO1")
        self.assertEqual(updated_discount.percentage, 20)

        # Verificar contra la base de datos
        refreshed = TicketDiscount.objects.get(pk=discount.pk)
        self.assertEqual(refreshed.code, "NUEVOCODIGO1")
        self.assertEqual(refreshed.percentage, 20)





