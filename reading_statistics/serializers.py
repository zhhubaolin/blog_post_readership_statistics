from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Article


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class ArticleSerializer(serializers.ModelSerializer):
    """文章序列化器"""
    author = UserSerializer(read_only=True)
    author_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'content', 'author', 'author_id',
            'created_at', 'updated_at', 'is_published'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ArticleListSerializer(serializers.ModelSerializer):
    """文章列表序列化器"""
    author = serializers.StringRelatedField()

    class Meta:
        model = Article
        fields = ['id', 'title', 'author', 'created_at', 'is_published']


class ReadingRecordRequestSerializer(serializers.Serializer):
    """阅读记录序列化器"""
    article_id = serializers.IntegerField()
    user_id = serializers.IntegerField(required=False, allow_null=True)
    ip_address = serializers.IPAddressField(required=False)
    user_agent = serializers.CharField(max_length=500, required=False)
    session_key = serializers.CharField(max_length=40, required=False)

    def validate_article_id(self, value):
        if not Article.objects.filter(id=value, is_published=True).exists():
            raise serializers.ValidationError('文章不存在或未发布')
        return value
