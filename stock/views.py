from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsActiveEmployee
from stock.repo.dealer_stock_api_repo import DealerStockApiRepo

repo = DealerStockApiRepo()


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsActiveEmployee])
def dealer_stock_list(request):
    if request.method == "GET":
        return repo.index(request)
    return repo.create(request)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsActiveEmployee])
def dealer_stock_detail(request, pk):
    return repo.delete(request, pk)
