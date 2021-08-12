"""
Module that contains utils for sql dbs
"""

import logging
from typing import (
    Optional
)


import sqlalchemy
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession
)
from sqlalchemy import (
    create_engine,
    select,
    insert,
    update,
    delete,
    Column,
    ForeignKey,
    Integer,
    String,
    Boolean
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session
)


DB_FILE = "booplibot.db"
ENGINE_URL = f"sqlite:///{DB_FILE}"
ENGINE_URL_ASYNC = f"sqlite+aiosqlite:///{DB_FILE}"

engine: sqlalchemy.engine.Engine = None
async_engine: sqlalchemy.ext.asyncio.AsyncEngine = None
SessionFactory: Session = None
AsyncSessionFactory: AsyncSession = None

Base = declarative_base()
metadata: sqlalchemy.MetaData = Base.metadata

logger = logging.getLogger(__name__)
inited = False


class GuildConfig(Base):
    """
    Represents a entry with the bot config per server
    """
    __tablename__ = "guild_config"

    guild_id = Column(Integer, nullable=False, primary_key=True)
    prefix = Column(String, nullable=False)
    enable_cc = Column(Boolean, nullable=False, server_default="0")
    log_channel = Column(Integer)
    welcome_channel = Column(Integer)
    system_channel = Column(Integer)

    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(guild_id={self.guild_id}, "
            f"prefix='{self.prefix}', "
            f"enable_cc={self.enable_cc}, "
            f"log_channel={self.log_channel}, "
            f"welcome_channel={self.welcome_channel}, "
            f"system_channel={self.system_channel})"
        )

guild_configs_table = GuildConfig.__table__

class User(Base):
    """
    Represents an entry with user data
    """
    __tablename__ = "user_data"

    guild_id = Column(Integer, ForeignKey(GuildConfig.guild_id), nullable=False, primary_key=True)
    user_id = Column(Integer,  nullable=False, primary_key=True)
    current_warns = Column(Integer, nullable=False, server_default="0")
    total_warns = Column(Integer, nullable=False, server_default="0")
    total_kicks = Column(Integer, nullable=False, server_default="0")
    total_bans = Column(Integer, nullable=False, server_default="0")

    __mapper_args__ = {"eager_defaults": True}

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(guild_id={self.guild_id}, "
            f"user_id={self.user_id}, "
            f"current_warns={self.current_warns}, "
            f"total_warns={self.total_warns}, "
            f"total_kicks={self.total_kicks}, "
            f"total_bans={self.total_bans})"
        )

user_data_table = User.__table__

class CustomCommand(Base):
    """
    Represents a custom commands entry
    """
    __tablename__ = "custom_command"

    guild_id = Column(Integer, ForeignKey(GuildConfig.guild_id), nullable=False, primary_key=True)
    command = Column(String, nullable=False)
    response = Column(String, nullable=False)
    # required_role_id = Column(Integer)

    # __mapper_args__ = {"eager_defaults": True}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(guild_id={self.guild_id}, command={self.command}, response={self.response})"

custom_command_table = CustomCommand.__table__


def init(should_log=True) -> None:
    """
    Inits sql dbs

    IN:
        should_log - whether or not we should log about successful init
    """
    global inited, engine, async_engine, SessionFactory, AsyncSessionFactory

    engine = create_engine(ENGINE_URL, echo=False, future=True)
    async_engine = create_async_engine(ENGINE_URL_ASYNC, echo=False, future=True)
    SessionFactory = sessionmaker(engine, class_=Session, future=True)
    AsyncSessionFactory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False, future=True)

    metadata.create_all(engine)

    inited = True

    if should_log:
        logger.info("SQL datebases inited.")

def deinit(should_log=True) -> None:
    """
    Deinits the sql dbs

    IN:
        should_log - whether or not we should log about successful deinit
    """
    global inited, engine, async_engine, SessionFactory, AsyncSessionFactory

    inited = False

    engine = None
    async_engine = None
    SessionFactory = None
    AsyncSessionFactory = None

    if should_log:
        logger.info("SQL datebases deinited.")

def NewSession(**kwargs) -> Optional[Session]:
    """
    Creates a session with our db

    IN:
        kwargs - additional kwargs for the factory
            Some of the supported arguments are:
                autoflush=True
                expire_on_commit=True

    OUT:
        Session object or None
    """
    if not inited:
        return None

    kwargs["future"] = True
    return SessionFactory(**kwargs)

def NewAsyncSession(**kwargs) -> Optional[AsyncSession]:
    """
    Creates a session with our db

    IN:
        kwargs - additional kwargs for the factory
            Some of the supported arguments are:
                autoflush=True
                expire_on_commit=False

    OUT:
        AsyncSession object or None
    """
    if not inited:
        return None

    kwargs["future"] = True
    return AsyncSessionFactory(**kwargs)

def to_dict(model) -> dict:
    """
    Converts an orm model to dict

    IN:
        model - the model to covnert

    OUT:
        dict with columns
    """
    rv = dict()
    columns = (col.name for col in model.__table__.columns)
    for col in columns:
        value = getattr(model, col)
        rv[col] = value

    return rv
