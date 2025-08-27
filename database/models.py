from sqlalchemy import (TIMESTAMP, String, Float, Integer, Boolean, BigInteger,
                        DateTime, Text, ForeignKey, func)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column, relationship)
from typing import List

class Base(DeclarativeBase):
    #created: Mapped[DateTime] = mapped_column(TIMESTAMP(timezone=True), default=func.now())
    updated: Mapped[DateTime] = mapped_column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=False, nullable=True)
    warnings_count: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default='False')

    created_listings: Mapped[List["Listing"]] = relationship(
        "Listing",
        foreign_keys="Listing.creator_user_id", # Явно указываем, по какому полю связывать
        back_populates="creator" # back_populates='creator' говорит, что это отношение связано с полем 'creator' в модели Listing.
    )

    purchased_listings: Mapped[List["Listing"]] = relationship(
        "Listing",
        foreign_keys="Listing.buyer_id",
        back_populates="buyer"
    )

class Listing(Base):
    __tablename__ = 'listings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_type: Mapped[str] = mapped_column(String(10), nullable=False)   
    lot_name: Mapped[str] = mapped_column(Text, nullable=False)
    lot_photo: Mapped[str] = mapped_column(String(150), nullable=False)
    lot_description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float(asdecimal=True), nullable=False)
    last_price: Mapped[float] = mapped_column(Float(asdecimal=True), nullable=True)
    start_time: Mapped[DateTime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    end_time: Mapped[DateTime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    creator_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[creator_user_id],
        back_populates="created_listings"
    )

    buyer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="purchased_listings"
    )
    # Зв'язок "один-до-багатьох": один Listing може мати багато PostedMessage
    posted_message: Mapped[List["PostedMessage"]] = relationship(back_populates="listing")
# ДОДАНО: Нова модель для зберігання інформації про кожне відправлене повідомлення
class PostedMessage(Base):
    __tablename__ = 'posted_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey('listings.id'))
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)

    listing: Mapped["Listing"] = relationship(back_populates="posted_message")
# ДОДАНО: Нова модель для зберігання ID груп, в яких є бот
class Group(Base):
    __tablename__ = 'groups'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=True)