from asyncio import sleep
from typing import Optional, Union, Literal

from httpx import AsyncClient, Timeout
from httpx import HTTPError, HTTPStatusError
from httpx._types import ProxyTypes
from json import JSONDecodeError

from rubipy.logger import logger
from rubipy.exceptions import RubikaAPIError, RubikaConnectionError


class Connection:
    """
    Asynchronous connection handler for communicating with the Rubika Bot API.

    This class manages establishing and closing HTTP connections, as well as constructing
    request URLs with proper token injection.

    Attributes:
        token (str): The bot's access token.
        base_url (str): Base URL for API requests. Defaults to Rubika Bot API endpoint.
        timeout (Timeout): Timeout settings for HTTP requests.
        max_retry (int): Number of retry attempts for failed requests.
        backoff_factor (float): Delay multiplier for retry attempts.
        proxy (Optional[ProxyTypes]): Optional HTTP proxy configuration.
    """

    TIMEOUT = 10
    BASE_URL = 'https://botapi.rubika.ir/v3'
    MAX_RETRY = 3
    BACKOFF_FACTOR = 0.5

    def __init__(
        self,
        token: str,
        base_url: Optional[str] = None,
        timeout: Optional[Union[float, int, Timeout]] = None,
        max_try: Optional[int] = None,
        backoff_factor: Optional[Union[float, int]] = None,
        proxy: Optional[ProxyTypes] = None
    ):
        """
        Initialize the Connection instance.

        Args:
            token (str): The bot token.
            base_url (Optional[str]): Custom base URL for the API.
            timeout (Optional[Union[float, int, Timeout]]): Request timeout value or config.
            max_try (Optional[int]): Maximum number of retry attempts.
            backoff_factor (Optional[Union[float, int]]): Delay multiplier for retries.
            proxy (Optional[ProxyTypes]): Proxy to use for requests.
        """

        self.token = token
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout if isinstance(timeout, Timeout) else Timeout(timeout or self.TIMEOUT)
        self.max_retry = max(1, max_try or self.MAX_RETRY)
        self.backoff_factor = max(0.0, backoff_factor or self.BACKOFF_FACTOR)
        self.proxy = proxy
        self._client: Optional[AsyncClient] = None
        self._is_connected: bool = False

    async def connect(self) -> None:
        """
        Establish an asynchronous HTTP connection using httpx.AsyncClient.

        Raises:
            RubikaConnectionError: If already connected.
        """

        if self._is_connected:
            raise RubikaConnectionError(f'{type(self).__name__} is Already connected')
        self._client = AsyncClient(timeout=self.timeout, proxy=self.proxy)
        self._is_connected = True

        logger.debug('Connection established.')

    async def request(
        self,
        endpoint: str,
        method: Literal['GET', 'POST'] = 'POST',
        payload: Optional[dict] = None
    ) -> dict:
        """
        Send an HTTP request to the Rubika Bot API with retry and exponential backoff.

        Args:
            endpoint (str): The API method name to call.
            method (Literal['GET', 'POST'], optional): HTTP method to use. Defaults to 'POST'.
            payload (Optional[dict], optional): JSON-serializable dictionary to send as the request body.

        Returns:
            dict: Parsed JSON response from the API.

        Raises:
            RubikaConnectionError: If the connection has not been established (i.e., 'connect()' was not called).
            RubikaAPIError: If the request fails after all retries or if the response contains invalid JSON.
        """

        if not self._client:
            raise RubikaConnectionError(f'{type(self).__name__} is not connected, call \'connect()\' first.')

        url = self._request_url(endpoint)

        logger.debug(f'[{endpoint}] Preparing {method} request to {url}' + (f' with payload: {payload}.' if payload else '.'))

        for attempt in range(1, self.max_retry + 1):
            logger.debug(f'attempt {attempt}/{self.max_retry} | [{method} -> {endpoint} | {url}]')

            try:
                response = await self._client.request(
                    method=method, url=url, json=payload
                )
                response.raise_for_status()

                try:
                    data = response.json()
                    status = data.get('status')

                    if status.upper() != 'OK':
                        message = data.get('dev_message', 'Unknown error')
                        logger.error(f'[{endpoint}] API error: status={status}, message={message}')
                        raise RubikaAPIError(f'[{endpoint}] API returned error status: {status} - {message}')

                    return data.get('data', {})
                except JSONDecodeError:
                    logger.warning(f'[{endpoint}] Invalid response error: Invalid response from Rubika Bot API.')
                    raise RubikaAPIError(f'[{endpoint}] Could not parse JSON from response')

            except HTTPStatusError as error:
                logger.error(f'[{endpoint}] HTTP status error: {error.response.status_code}: {error.response.text}')
            except HTTPError as error:
                logger.warning(f'[{endpoint}] Network error: {str(error)} (attempt {attempt}/{self.max_retry})')

            wait_for = self.backoff_factor * (2 ** (attempt - 1))
            logger.debug(f'[{endpoint}] Waiting {wait_for:.2f}s before retrying...')
            await sleep(wait_for)

        raise RubikaAPIError(f'[{endpoint}] Request failed after {self.max_retry} attempts.')

    async def disconnect(self) -> None:
        """
        Close the HTTP connection and clean up resources.

        Raises:
            RubikaConnectionError: If not connected.
        """

        if not self._is_connected:
            raise RubikaConnectionError(f'{type(self).__name__} is already disconnected')
        self._is_connected = False
        await self._client.aclose()
        self._client = None

        logger.debug('Connection closed.')

    def _request_url(self, endpoint: str) -> str:
        """
        Construct the full API request URL.

        Args:
            endpoint (str): The API method name.

        Returns:
            str: Full URL to be used in the HTTP request.
        """

        return f'{self.base_url}/{self.token}/{endpoint}'