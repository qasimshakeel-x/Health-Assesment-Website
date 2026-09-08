from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    Text, ForeignKey, DateTime, CheckConstraint, Index, ARRAY, Computed
)
from sqlalchemy.dialects.postgresql import JSONB, INTEGER as PG_INTEGER
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/longevity_platform")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(20), default="user")
    age = Column(Integer, nullable=True)
    gender = Column(Integer, nullable=True)  # 0=Female, 1=Male
    created_at = Column(DateTime, default=datetime.utcnow)
    profiles = relationship("UserProfile", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(Integer, nullable=False)  # 0=Female, 1=Male
    height = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)
    bmi = Column(Float, Computed("weight / POWER(height / 100.0, 2)", persisted=True))
    sleep_hours = Column(Float, nullable=False)
    exercise_level = Column(Integer, nullable=False)
    smoking = Column(Boolean, default=False)
    alcohol = Column(Integer, default=0)
    family_history = Column(ARRAY(PG_INTEGER), default=[0, 0, 0, 0])
    phq9 = Column(ARRAY(PG_INTEGER), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profiles")
    predictions = relationship("PredictionResult", back_populates="profile", cascade="all, delete-orphan")
    reports = relationship("ReportLog", back_populates="profile", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("age BETWEEN 18 AND 120", name="check_age"),
        CheckConstraint("sleep_hours BETWEEN 3.0 AND 12.0", name="check_sleep"),
        CheckConstraint("exercise_level BETWEEN 0 AND 4", name="check_exercise"),
        CheckConstraint("alcohol BETWEEN 0 AND 7", name="check_alcohol"),
        CheckConstraint("gender IN (0, 1)", name="check_gender"),
    )

    @property
    def computed_bmi(self):
        if self.height and self.weight:
            return self.weight / (self.height / 100.0) ** 2
        return None


class PredictionResult(Base):
    __tablename__ = "prediction_results"
    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    diabetes_risk = Column(Float)
    heart_risk = Column(Float)
    hypertension_risk = Column(Float)
    obesity_risk = Column(Float)
    biological_age = Column(Float)
    longevity_score = Column(Float)
    depression_level = Column(String(20))
    depression_confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="predictions")
    shap_explanations = relationship("SHAPExplanation", back_populates="prediction", cascade="all, delete-orphan")
    chat_session = relationship("ChatSession", back_populates="prediction", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_prediction_results_user_profile_id", "user_profile_id"),
    )


class SHAPExplanation(Base):
    __tablename__ = "shap_explanations"
    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("prediction_results.id", ondelete="CASCADE"), nullable=False)
    disease = Column(String(50), nullable=False)
    feature_name = Column(String(100), nullable=False)
    shap_value = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)

    prediction = relationship("PredictionResult", back_populates="shap_explanations")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("prediction_results.id", ondelete="CASCADE"), nullable=False, unique=True)
    messages = Column(JSONB, default=[])
    system_prompt = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    prediction = relationship("PredictionResult", back_populates="chat_session")


class ReportLog(Base):
    __tablename__ = "report_log"
    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    pdf_path = Column(String(512))
    generated_at = Column(DateTime, default=datetime.utcnow)
    file_size_kb = Column(Float)
    status = Column(String(20), default="pending")

    profile = relationship("UserProfile", back_populates="reports")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
