# from telegram.ext import BasePersistence
from google.cloud import storage


import json
from collections import defaultdict
from copy import deepcopy
from typing import Any, DefaultDict, Dict, Optional, Tuple

from telegram.ext import BasePersistence
from telegram.utils.types import ConversationDict
import google.cloud.exceptions as exceptions


class GoogleCloudStoragePersistence(BasePersistence):
    storage_client = storage.Client()

    def __init__(
        self,
        bucketname: str,      #Should be bucket and/or blob name
        filename: str,
        store_user_data: bool = True,
        store_chat_data: bool = True,
        store_bot_data: bool = True,
        single_file: bool = True,           #If false, stores in chatID_user_data.json, chatID_chat_data.json, chatID_bot_data.json
        on_flush: bool = False,
        storage_client: storage.Client = storage.Client()
    ):
        super().__init__(
            store_user_data=store_user_data,
            store_chat_data=store_chat_data,
            store_bot_data=store_bot_data,
        )
        self.bucketname = bucketname
        self.filename = filename
        try:
            self.bucket = storage_client.get_bucket(bucketname)
        except:
            
            self.bucket = storage_client.create_bucket(bucketname)
            blob = self.bucket.blob(filename)
            blob.upload_from_string(json.dumps({}))
        self.filename = filename 
        self.storage_client = storage_client

        self.single_file = single_file
        self.on_flush = on_flush
        self.user_data: Optional[DefaultDict[int, Dict]] = None
        self.chat_data: Optional[DefaultDict[int, Dict]] = None
        self.bot_data: Optional[Dict] = None
        self.conversations: Optional[Dict[str, Dict[Tuple, object]]] = None



    def get_bot_data(self) -> Dict[object, object]:
        """Returns the bot_data from the bucket's blob if it exists or an empty :obj:`dict`.
        Returns:
            :obj:`dict`: The restored bot data.
        """
        if self.bot_data:
            pass
        elif not self.single_file:
            bucketname = f"{self.bucketname}_bot_data"
            data = self._load_file(bucketname)
            if not data:
                data = {}
            self.bot_data = data
        else:
            self._load_singlefile()
        return deepcopy(self.bot_data)  # type: ignore[arg-type]

    def _load_singlefile(self) -> None:
        try:
            ''' This loads the data from a file '''

            bucketname = self.bucketname
            data = json.loads(self.bucket.get_blob(self.filename).download_as_string())
            self.user_data = defaultdict(dict, data['user_data'])
            self.chat_data = defaultdict(dict, data['chat_data'])
            # For backwards compatibility with files not containing bot data
            self.bot_data = data.get('bot_data', {})
            self.conversations = data['conversations']

            filename = self.filename
            # with open(self.filename, "rb") as file:
            #     data = pickle.load(file)
            #     self.user_data = defaultdict(dict, data['user_data'])
            #     self.chat_data = defaultdict(dict, data['chat_data'])
            #     # For backwards compatibility with files not containing bot data
            #     self.bot_data = data.get('bot_data', {})
            #     self.conversations = data['conversations']
        except KeyError:
            self.conversations = {}
            self.user_data = defaultdict(dict)
            self.chat_data = defaultdict(dict)
            self.bot_data = {}
        # except pickle.UnpicklingError as exc:
        #     raise TypeError(f"File {filename} does not contain valid pickle data") from exc
        # except Exception as exc:
        #     raise TypeError(f"Something went wrong unpickling {filename}") from exc    

    def _load_file(filename: str) -> Any:
        pass
        # try:
        #     with open(filename, "rb") as file:
        #         return pickle.load(file)
        # except OSError:
        #     return None
        # except pickle.UnpicklingError as exc:
        #     raise TypeError(f"File {filename} does not contain valid pickle data") from exc
        # except Exception as exc:
        #     raise TypeError(f"Something went wrong unpickling {filename}") from exc

    def _dump_singlefile(self) -> None:

        filename = self.filename
        data = {
                'conversations': self.conversations,
                'user_data': self.user_data,
                'chat_data': self.chat_data,
                'bot_data': self.bot_data,
            }
        self.bucket.get_blob(filename).upload_from_string(json.dumps(data))

    def _dump_file(filename: str) -> Any:
        pass

    def update_bot_data(self, data: Dict) -> None:
        """Will update the bot_data and depending on :attr:`on_flush` save the pickle file.
        Args:
            data (:obj:`dict`): The :attr:`telegram.ext.dispatcher.bot_data`.
        """
        if self.bot_data == data:
            return
        self.bot_data = data.copy()
        if not self.on_flush:
            if not self.single_file:
                bucketname = f"{self.bucketname}_bot_data"
                self._dump_file(bucketname, self.bot_data)
            else:
                self._dump_singlefile()


    def get_chat_data(self) -> DefaultDict[int, Dict[object, object]]:
        """Returns the chat_data from the pickle file if it exists or an empty :obj:`defaultdict`.
        Returns:
            :obj:`defaultdict`: The restored chat data.
        """
        if self.chat_data:
            pass
        elif not self.single_file:
            bucketname = f"{self.bucketname}_chat_data"
            data = self._load_file(bucketname)
            if not data:
                data = defaultdict(dict)
            else:
                data = defaultdict(dict, data)
            self.chat_data = data
        else:
            self._load_singlefile()
        return deepcopy(self.chat_data)  # type: ignore[arg-type]

    
    def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """Will update the chat_data and depending on :attr:`on_flush` save the pickle file.
        Args:
            chat_id (:obj:`int`): The chat the data might have been changed for.
            data (:obj:`dict`): The :attr:`telegram.ext.dispatcher.chat_data` [chat_id].
        """
        if self.chat_data is None:
            self.chat_data = defaultdict(dict)
        if self.chat_data.get(chat_id) == data:
            return
        self.chat_data[chat_id] = data
        if not self.on_flush:
            if not self.single_file:
                bucketname = f"{self.bucketname}_chat_data"
                self._dump_file(bucketname, self.chat_data)
            else:
                self._dump_singlefile()

    def get_user_data(self) -> DefaultDict[int, Dict[object, object]]:
        """Returns the user_data from the pickle file if it exists or an empty :obj:`defaultdict`.
        Returns:
            :obj:`defaultdict`: The restored user data.
        """
        if self.user_data:
            pass
        elif not self.single_file:
            bucketname = f"{self.bucketname}_user_data"
            data = self._load_file(bucketname)
            if not data:
                data = defaultdict(dict)
            else:
                data = defaultdict(dict, data)
            self.user_data = data
        else:
            self._load_singlefile()
        return deepcopy(self.user_data)  # type: ignore[arg-type]

    def update_user_data(self, user_id: int, data: Dict) -> None:
        """Will update the user_data and depending on :attr:`on_flush` save the pickle file.
        Args:
            user_id (:obj:`int`): The user the data might have been changed for.
            data (:obj:`dict`): The :attr:`telegram.ext.dispatcher.user_data` [user_id].
        """
        if self.user_data is None:
            self.user_data = defaultdict(dict)
        if self.user_data.get(user_id) == data:
            return
        self.user_data[user_id] = data
        if not self.on_flush:
            if not self.single_file:
                bucketname = f"{self.bucketname}_user_data"
                self._dump_file(bucketname, self.user_data)
            else:
                self._dump_singlefile()


    def get_conversations(self, name: str) -> ConversationDict:
        """Returns the conversations from the pickle file if it exsists or an empty dict.
        Args:
            name (:obj:`str`): The handlers name.
        Returns:
            :obj:`dict`: The restored conversations for the handler.
        """
        if self.conversations:
            pass
        elif not self.single_file:
            bucketname = f"{self.bucketname}_conversations"
            data = self._load_file(bucketname)
            if not data:
                data = {name: {}}
            self.conversations = data
        else:
            self._load_singlefile()
        return self.conversations.get(name, {}).copy()  # type: ignore[union-attr]

    def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[object]
    ) -> None:
        """Will update the conversations for the given handler and depending on :attr:`on_flush`
        save the pickle file.
        Args:
            name (:obj:`str`): The handler's name.
            key (:obj:`tuple`): The key the state is changed for.
            new_state (:obj:`tuple` | :obj:`any`): The new state for the given key.
        """
        if not self.conversations:
            self.conversations = {}
        if self.conversations.setdefault(name, {}).get(key) == new_state:
            return
        self.conversations[name][key] = new_state
        if not self.on_flush:
            if not self.single_file:
                bucketname = f"{self.bucketname}_conversations"
                self._dump_file(bucketname, self.conversations)
            else:
                self._dump_singlefile()


    def flush(self) -> None:
        """Will save all data in memory to pickle file(s)."""
        if self.single_file:
            if self.user_data or self.chat_data or self.bot_data or self.conversations:
                self._dump_singlefile()
        else:
            if self.user_data:
                self._dump_file(f"{self.bucketname}_user_data", self.user_data)
            if self.chat_data:
                self._dump_file(f"{self.bucketname}_chat_data", self.chat_data)
            if self.bot_data:
                self._dump_file(f"{self.bucketname}_bot_data", self.bot_data)
            if self.conversations:
                self._dump_file(f"{self.bucketname}_conversations", self.conversations)
'''
    * :meth:`get_bot_data`
    * :meth:`update_bot_data`
    * :meth:`get_chat_data`
    * :meth:`update_chat_data`
    * :meth:`get_user_data`
    * :meth:`update_user_data`
    * :meth:`get_conversations`
    * :meth:`update_conversation`
    * :meth:`flush`
'''

