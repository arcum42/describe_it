from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(2048), default="")
    trigger_word: Mapped[str] = mapped_column(String(255), default="")
    caption_mode: Mapped[str] = mapped_column(String(32), default="description")
    context_url: Mapped[str] = mapped_column(String(2048), default="")
    context_file_path: Mapped[str] = mapped_column(String(2048), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    images: Mapped[list["ImageRecord"]] = relationship(back_populates="project")
    prompts: Mapped[list["PromptRecord"]] = relationship(back_populates="project")
    presets: Mapped[list["PresetRecord"]] = relationship(back_populates="project")


class ImageRecord(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    original_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    working_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    included: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id"), nullable=True)
    project: Mapped[ProjectRecord] = relationship(back_populates="images")
    captions: Mapped[list["CaptionRecord"]] = relationship(back_populates="image")


class CaptionRecord(Base):
    __tablename__ = "captions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(255), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=datetime.utcnow)
    image: Mapped[ImageRecord] = relationship(back_populates="captions")


class PromptRecord(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, default="")
    project: Mapped[ProjectRecord] = relationship(back_populates="prompts")


class PresetRecord(Base):
    __tablename__ = "presets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    backend: Mapped[str] = mapped_column(String(64), default="")
    model_name: Mapped[str] = mapped_column(String(255), default="")
    prompt_id: Mapped[int | None] = mapped_column(ForeignKey("prompts.id"), nullable=True)
    project: Mapped[ProjectRecord] = relationship(back_populates="presets")
