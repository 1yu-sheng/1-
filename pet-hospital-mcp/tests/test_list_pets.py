import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pet_hospital_mcp.rest_client import PetHospitalClient, BackendError


def make_response(status_code, body):
    return httpx.Response(
        status_code=status_code,
        json=body,
    )


@pytest.fixture
def client():
    return PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=2)


@pytest.mark.asyncio
async def test_list_pets_success():
    response_data = {
        "code": 200,
        "message": "ok",
        "data": {
            "items": [
                {"id": "PET-000001", "name": "旺财", "species": "犬", "totalCost": 500.0}
            ],
            "total": 1,
            "page": 1,
            "pageSize": 10,
            "totalPages": 1,
            "totalCost": 500.0,
        },
        "time": "2025-01-01T00:00:00+08:00",
    }

    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=1)

    def handler(request):
        return make_response(200, response_data)

    mock_transport = httpx.MockTransport(handler)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    result = await test_client.list_pets(species="犬", page=1, pageSize=10)
    assert result.total == 1
    assert result.items[0].id == "PET-000001"


@pytest.mark.asyncio
async def test_list_pets_all_params_forwarded():
    response_data = {
        "code": 200,
        "message": "ok",
        "data": {
            "items": [],
            "total": 0,
            "page": 1,
            "pageSize": 5,
            "totalPages": 0,
            "totalCost": 0.0,
        },
        "time": "2025-01-01T00:00:00+08:00",
    }

    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=1)

    captured_params = {}

    def capture_request(request):
        captured_params.update(dict(request.url.params))
        return make_response(200, response_data)

    mock_transport = httpx.MockTransport(capture_request)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    await test_client.list_pets(
        q="test", name="旺财", ownerName="张三", ownerPhone="13800001111",
        species="犬", doctor="李医生", disease="肠胃炎", status="待就诊",
        min=100, max=5000, sortBy="totalCost", order="desc",
        page=2, pageSize=5,
    )

    assert captured_params["species"] == "犬"
    assert captured_params["page"] == "2"
    assert captured_params["pageSize"] == "5"
    assert captured_params["sortBy"] == "totalCost"
    assert captured_params["order"] == "desc"
    assert captured_params["min"] == "100"
    assert captured_params["max"] == "5000"


@pytest.mark.asyncio
async def test_list_pets_backend_4xx():
    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=1)

    def error_request(request):
        return make_response(404, {"code": 404, "message": "not found", "data": {}, "time": ""})

    mock_transport = httpx.MockTransport(error_request)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    with pytest.raises(BackendError) as exc_info:
        await test_client.list_pets()
    assert exc_info.value.code == "BACKEND_API_ERROR"


@pytest.mark.asyncio
async def test_list_pets_backend_5xx_retry_then_fail():
    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=2)

    call_count = 0
    def error_request(request):
        nonlocal call_count
        call_count += 1
        return make_response(500, {"code": 500, "message": "server error", "data": {}, "time": ""})

    mock_transport = httpx.MockTransport(error_request)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    with pytest.raises(BackendError) as exc_info:
        await test_client.list_pets()
    assert exc_info.value.code == "BACKEND_API_ERROR"
    assert call_count == 2


@pytest.mark.asyncio
async def test_list_pets_timeout():
    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=1)

    def timeout_request(request):
        raise httpx.TimeoutException("timeout")

    mock_transport = httpx.MockTransport(timeout_request)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    with pytest.raises(BackendError) as exc_info:
        await test_client.list_pets()
    assert exc_info.value.code == "BACKEND_TIMEOUT"


@pytest.mark.asyncio
async def test_list_pets_connect_error():
    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=1)

    def connect_error_request(request):
        raise httpx.ConnectError("connection refused")

    mock_transport = httpx.MockTransport(connect_error_request)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    with pytest.raises(BackendError) as exc_info:
        await test_client.list_pets()
    assert exc_info.value.code == "BACKEND_UNAVAILABLE"


@pytest.mark.asyncio
async def test_list_pets_invalid_json():
    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=1)

    def bad_request(request):
        return httpx.Response(status_code=200, content=b"not json")

    mock_transport = httpx.MockTransport(bad_request)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    with pytest.raises(BackendError) as exc_info:
        await test_client.list_pets()
    assert exc_info.value.code == "BACKEND_INVALID_RESPONSE"


@pytest.mark.asyncio
async def test_list_pets_data_model_mismatch():
    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=1)

    response_data = {
        "code": 200,
        "message": "ok",
        "data": {
            "items": [{"species": "犬"}],
            "total": 1,
            "page": 1,
            "pageSize": 10,
            "totalPages": 1,
            "totalCost": 0.0,
        },
        "time": "2025-01-01T00:00:00+08:00",
    }

    def mismatch_request(request):
        return make_response(200, response_data)

    mock_transport = httpx.MockTransport(mismatch_request)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    with pytest.raises(BackendError) as exc_info:
        await test_client.list_pets()
    assert exc_info.value.code == "BACKEND_INVALID_RESPONSE"


@pytest.mark.asyncio
async def test_list_pets_non_200_code():
    from pet_hospital_mcp.rest_client import PetHospitalClient
    test_client = PetHospitalClient(base_url="http://127.0.0.1:8080", timeout=5.0, max_retries=1)

    response_data = {
        "code": 500,
        "message": "internal error",
        "data": {},
        "time": "2025-01-01T00:00:00+08:00",
    }

    def error_request(request):
        return make_response(200, response_data)

    mock_transport = httpx.MockTransport(error_request)
    test_client._client = httpx.AsyncClient(transport=mock_transport, base_url="http://127.0.0.1:8080")

    with pytest.raises(BackendError) as exc_info:
        await test_client.list_pets()
    assert exc_info.value.code == "BACKEND_API_ERROR"


def test_list_pets_input_validation():
    from pet_hospital_mcp.tools.list_pets import ListPetsInput, validate_list_pets_input

    input_data = validate_list_pets_input(
        species="犬", status="待就诊", page=1, pageSize=10, sortBy="totalCost", order="desc"
    )
    assert input_data.species == "犬"
    assert input_data.status == "待就诊"


def test_list_pets_input_validation_invalid_species():
    from pet_hospital_mcp.tools.list_pets import ListPetsInput
    with pytest.raises(Exception):
        ListPetsInput(species="invalid")


def test_list_pets_input_validation_invalid_status():
    from pet_hospital_mcp.tools.list_pets import ListPetsInput
    with pytest.raises(Exception):
        ListPetsInput(status="invalid")


def test_list_pets_input_validation_page_lt_1():
    from pet_hospital_mcp.tools.list_pets import ListPetsInput
    with pytest.raises(Exception):
        ListPetsInput(page=0)


def test_list_pets_input_validation_pageSize_out_of_range():
    from pet_hospital_mcp.tools.list_pets import ListPetsInput
    with pytest.raises(Exception):
        ListPetsInput(pageSize=501)


def test_list_pets_input_validation_min_gt_max():
    from pet_hospital_mcp.tools.list_pets import ListPetsInput
    with pytest.raises(Exception):
        ListPetsInput(min=100, max=50)


def test_list_pets_input_validation_extra_field():
    from pet_hospital_mcp.tools.list_pets import ListPetsInput
    with pytest.raises(Exception):
        ListPetsInput(unknown_field="test")


def test_list_pets_input_validation_negative_min():
    from pet_hospital_mcp.tools.list_pets import ListPetsInput
    with pytest.raises(Exception):
        ListPetsInput(min=-1)