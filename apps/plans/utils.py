def build_absolute_image_url(request, image_field):
    """
    گرفتن URL کامل تصویر یا رشته خالی اگر وجود نداشت.
    """
    if image_field and hasattr(image_field, 'url'):
        return request.build_absolute_uri(image_field.url)
    return ""
