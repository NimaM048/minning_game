from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ContactInfo
from .serializers import ContactInfoSerializer
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAdminUser


class ContactInfoView(APIView):


    """
    API برای دریافت، ایجاد یا بروزرسانی اطلاعات تماس و درباره ما
    """

    def get(self, request):
        contact = ContactInfo.objects.first()
        if not contact:
            return Response({"detail": "اطلاعات تماس ثبت نشده است"}, status=404)
        return Response(ContactInfoSerializer(contact).data)

    @swagger_auto_schema(
        request_body=ContactInfoSerializer,
        operation_description="ثبت اطلاعات تماس و درباره ما (فقط توسط ادمین)",
        responses={201: ContactInfoSerializer()}
    )
    def post(self, request):
        serializer = ContactInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if ContactInfo.objects.exists():
            return Response({"detail": "اطلاعات تماس قبلاً ثبت شده است. از PUT برای بروزرسانی استفاده کنید."},
                            status=400)

        contact = serializer.save()
        return Response(ContactInfoSerializer(contact).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=ContactInfoSerializer,
        operation_description="ویرایش اطلاعات تماس و درباره ما (فقط توسط ادمین)",
        responses={200: ContactInfoSerializer()}
    )
    def put(self, request):
        contact = ContactInfo.objects.first()
        if not contact:
            return Response({"detail": "اطلاعات تماس یافت نشد. ابتدا با POST ایجاد کنید."}, status=404)

        serializer = ContactInfoSerializer(contact, data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        return Response(ContactInfoSerializer(contact).data)
