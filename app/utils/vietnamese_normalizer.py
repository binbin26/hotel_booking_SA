"""
═══════════════════════════════════════════════════════════════════════════
VIETNAMESE TEXT UNICODE NORMALIZATION - BACKEND UTILITY
═══════════════════════════════════════════════════════════════════════════

This module handles Unicode normalization for Vietnamese text on the backend.

Problem: Vietnamese text sometimes uses NFD (decomposed form) instead of NFC
(composed form), causing rendering issues like "đến" appearing as "đế n".

Solution: Normalize all Vietnamese text to NFC (composed form) before sending
to the frontend or storing in the database.

Usage:
    from app.utils.vietnamese_normalizer import normalize_vietnamese_text, normalize_dict

    # Normalize a single string
    name = normalize_vietnamese_text(user_name)

    # Normalize a dictionary (for API responses)
    booking_data = normalize_dict(booking.dict())

    # Use as middleware/dependency for automatic normalization
    from app.utils.vietnamese_normalizer import NormalizationMiddleware
"""

import unicodedata
from typing import Any, Dict, List, Union, Optional


# ──────────────────────────────────────────────────────────────────────────
# 1. CORE NORMALIZATION FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────

def normalize_vietnamese_text(text: Union[str, None], form: str = 'NFC') -> Union[str, None]:
    """
    Normalize Vietnamese text to NFC (composed form) or NFD (decomposed form).
    
    Args:
        text: The text string to normalize (or None)
        form: Normalization form - 'NFC' (default), 'NFD', 'NFKC', 'NFKD'
              NFC: Composed form (preferred for rendering)
              NFD: Decomposed form (can cause rendering issues)
    
    Returns:
        Normalized text string, or None if input is None
        
    Example:
        >>> normalize_vietnamese_text("Tiếng Việt")
        'Tiếng Việt'
        
        >>> normalize_vietnamese_text("Tiếng Việt", form='NFD')
        'Tiếng Việt'  # Decomposed form (internally different)
    """
    if not text or not isinstance(text, str):
        return text
    
    try:
        # Normalize to specified form
        normalized = unicodedata.normalize(form, text)
        return normalized
    except (TypeError, ValueError) as e:
        print(f"Error normalizing text: {e}")
        return text


def is_normalized(text: Union[str, None], form: str = 'NFC') -> bool:
    """
    Check if text is already normalized in the specified form.
    
    Args:
        text: The text to check
        form: Normalization form to check against ('NFC', 'NFD', 'NFKC', 'NFKD')
    
    Returns:
        True if text is normalized in the specified form
    """
    if not text or not isinstance(text, str):
        return True
    
    return text == unicodedata.normalize(form, text)


def detect_normalization_form(text: Union[str, None]) -> Optional[str]:
    """
    Detect the normalization form of a given text.
    
    Args:
        text: The text to analyze
    
    Returns:
        'NFC', 'NFD', 'NFKC', 'NFKD', or None if cannot determine
    """
    if not text or not isinstance(text, str):
        return None
    
    forms = ['NFC', 'NFD', 'NFKC', 'NFKD']
    for form in forms:
        if text == unicodedata.normalize(form, text):
            return form
    
    return None


def has_vietnamese_characters(text: Union[str, None]) -> bool:
    """
    Check if text contains Vietnamese characters.
    
    Vietnamese character ranges in Unicode:
    - Lowercase: ă â ê ô ơ ư đ
    - With diacritics: à á ả ã ạ ầ ấ ẩ ẫ ậ etc.
    - Full range: U+00C0-U+017F, U+1E00-U+1EFF
    
    Args:
        text: The text to check
    
    Returns:
        True if text contains Vietnamese characters
    """
    if not text or not isinstance(text, str):
        return False
    
    # Vietnamese character ranges
    vietnamese_ranges = [
        (0x00C0, 0x017F),  # Latin Extended A
        (0x1E00, 0x1EFF),  # Latin Extended Additional (includes all Vietnamese)
    ]
    
    for char in text:
        code_point = ord(char)
        for start, end in vietnamese_ranges:
            if start <= code_point <= end:
                return True
    
    return False


# ──────────────────────────────────────────────────────────────────────────
# 2. COLLECTION NORMALIZATION
# ──────────────────────────────────────────────────────────────────────────

def normalize_dict(
    data: Union[Dict[str, Any], None],
    recursive: bool = True,
    only_vietnamese: bool = False
) -> Union[Dict[str, Any], None]:
    """
    Normalize all string values in a dictionary.
    
    Args:
        data: Dictionary to normalize
        recursive: If True, normalize nested dicts and lists
        only_vietnamese: If True, only normalize strings containing Vietnamese
    
    Returns:
        Dictionary with all strings normalized to NFC
        
    Example:
        >>> booking = {"guest": "Tiếng Việt", "address": "Hà Nội"}
        >>> normalize_dict(booking)
        {"guest": "Tiếng Việt", "address": "Hà Nội"}
    """
    if not data or not isinstance(data, dict):
        return data
    
    normalized = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            if only_vietnamese:
                if has_vietnamese_characters(value):
                    normalized[key] = normalize_vietnamese_text(value)
                else:
                    normalized[key] = value
            else:
                normalized[key] = normalize_vietnamese_text(value)
        elif isinstance(value, dict) and recursive:
            normalized[key] = normalize_dict(value, recursive, only_vietnamese)
        elif isinstance(value, list) and recursive:
            normalized[key] = normalize_list(value, recursive, only_vietnamese)
        else:
            normalized[key] = value
    
    return normalized


def normalize_list(
    data: Union[List[Any], None],
    recursive: bool = True,
    only_vietnamese: bool = False
) -> Union[List[Any], None]:
    """
    Normalize all string values in a list.
    
    Args:
        data: List to normalize
        recursive: If True, normalize nested dicts and lists
        only_vietnamese: If True, only normalize strings containing Vietnamese
    
    Returns:
        List with all strings normalized to NFC
    """
    if not data or not isinstance(data, list):
        return data
    
    normalized = []
    
    for item in data:
        if isinstance(item, str):
            if only_vietnamese:
                if has_vietnamese_characters(item):
                    normalized.append(normalize_vietnamese_text(item))
                else:
                    normalized.append(item)
            else:
                normalized.append(normalize_vietnamese_text(item))
        elif isinstance(item, dict) and recursive:
            normalized.append(normalize_dict(item, recursive, only_vietnamese))
        elif isinstance(item, list) and recursive:
            normalized.append(normalize_list(item, recursive, only_vietnamese))
        else:
            normalized.append(item)
    
    return normalized


# ──────────────────────────────────────────────────────────────────────────
# 3. PYDANTIC MODEL NORMALIZATION (FOR FASTAPI SCHEMAS)
# ──────────────────────────────────────────────────────────────────────────

def normalize_pydantic_model(model: Any, only_vietnamese: bool = False) -> Any:
    """
    Normalize all string fields in a Pydantic model.
    
    Args:
        model: Pydantic model instance to normalize
        only_vietnamese: If True, only normalize strings containing Vietnamese
    
    Returns:
        Normalized copy of the model
        
    Example:
        >>> from pydantic import BaseModel
        >>> class Guest(BaseModel):
        ...     name: str
        ...     email: str
        >>> guest = Guest(name="Tiếng Việt", email="test@example.com")
        >>> normalize_pydantic_model(guest)
    """
    try:
        # Convert to dict, normalize, convert back
        data = model.dict() if hasattr(model, 'dict') else model.model_dump()
        normalized_data = normalize_dict(data, recursive=True, only_vietnamese=only_vietnamese)
        
        # Create new instance with normalized data
        model_class = type(model)
        return model_class(**normalized_data)
    except Exception as e:
        print(f"Error normalizing Pydantic model: {e}")
        return model


# ──────────────────────────────────────────────────────────────────────────
# 4. UTILITY FUNCTIONS FOR DEBUGGING
# ──────────────────────────────────────────────────────────────────────────

def analyze_text(text: Union[str, None]) -> Dict[str, Any]:
    """
    Analyze a text string for Unicode normalization issues.
    
    Args:
        text: Text to analyze
    
    Returns:
        Dictionary with analysis results
        
    Example:
        >>> analyze_text("Tiếng Việt")
        {
            'original': 'Tiếng Việt',
            'length_nfc': 9,
            'length_nfd': 14,
            'is_nfc': True,
            'has_vietnamese': True,
            'detected_form': 'NFC'
        }
    """
    if not text or not isinstance(text, str):
        return {}
    
    return {
        'original': text,
        'length': len(text),
        'length_nfc': len(unicodedata.normalize('NFC', text)),
        'length_nfd': len(unicodedata.normalize('NFD', text)),
        'is_nfc': is_normalized(text, 'NFC'),
        'is_nfd': is_normalized(text, 'NFD'),
        'has_vietnamese': has_vietnamese_characters(text),
        'detected_form': detect_normalization_form(text),
        'char_codes': [ord(c) for c in text],
    }


def log_text_analysis(text: Union[str, None], label: str = "") -> None:
    """
    Log analysis of a text string for debugging.
    
    Args:
        text: Text to analyze
        label: Optional label for the log
    """
    analysis = analyze_text(text)
    if analysis:
        label_str = f" ({label})" if label else ""
        print(f"\n{'='*70}")
        print(f"Vietnamese Text Analysis{label_str}")
        print(f"{'='*70}")
        for key, value in analysis.items():
            print(f"{key:20s}: {value}")
        print(f"{'='*70}\n")


# ──────────────────────────────────────────────────────────────────────────
# 5. FASTAPI DEPENDENCY & MIDDLEWARE UTILITIES
# ──────────────────────────────────────────────────────────────────────────

def get_normalized_text_dependency(
    text: str,
    only_vietnamese: bool = False
) -> str:
    """
    FastAPI dependency for automatic Vietnamese text normalization.
    
    Usage in router:
        from fastapi import Depends
        from app.utils.vietnamese_normalizer import get_normalized_text_dependency
        
        @router.post("/guests")
        def create_guest(name: str = Depends(get_normalized_text_dependency)):
            # name is automatically normalized to NFC
            return {"name": name}
    
    Args:
        text: Input text
        only_vietnamese: Only normalize if contains Vietnamese
    
    Returns:
        Normalized text
    """
    if only_vietnamese and not has_vietnamese_characters(text):
        return text
    
    return normalize_vietnamese_text(text)


# ──────────────────────────────────────────────────────────────────────────
# 6. CONTEXT MANAGERS FOR BATCH NORMALIZATION
# ──────────────────────────────────────────────────────────────────────────

class NormalizeVietnameseContext:
    """
    Context manager for batch normalizing Vietnamese text.
    
    Usage:
        with NormalizeVietnameseContext() as normalizer:
            text1 = normalizer("Tiếng Việt")
            text2 = normalizer("Hà Nội")
    """
    
    def __init__(self, form: str = 'NFC', only_vietnamese: bool = False):
        self.form = form
        self.only_vietnamese = only_vietnamese
        self.count = 0
    
    def __enter__(self):
        def normalize(text):
            if self.only_vietnamese and not has_vietnamese_characters(text):
                return text
            
            self.count += 1
            return normalize_vietnamese_text(text, self.form)
        
        return normalize
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.count > 0:
            print(f"Normalized {self.count} text strings to {self.form}")
        return False


# ──────────────────────────────────────────────────────────────────────────
# 7. INTEGRATION WITH DATABASE/ORM
# ──────────────────────────────────────────────────────────────────────────

def normalize_model_fields(model_instance: Any, field_names: List[str]) -> None:
    """
    Normalize specific fields on a SQLAlchemy or similar model.
    
    Args:
        model_instance: Model instance to normalize
        field_names: List of field names to normalize
        
    Example:
        >>> user = User(name="Tiếng Việt", email="test@example.com")
        >>> normalize_model_fields(user, ['name'])
        >>> # user.name is now normalized
    """
    for field_name in field_names:
        if hasattr(model_instance, field_name):
            value = getattr(model_instance, field_name)
            if isinstance(value, str):
                normalized = normalize_vietnamese_text(value)
                setattr(model_instance, field_name, normalized)


# ──────────────────────────────────────────────────────────────────────────
# 8. PRE/POST HOOKS FOR SQLALCHEMY
# ──────────────────────────────────────────────────────────────────────────

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import event
    from sqlalchemy.orm.attributes import InstrumentedAttribute
    
    def create_normalization_listener(model_class: Any, field_names: List[str]):
        """
        Create a SQLAlchemy event listener for automatic Vietnamese normalization.
        
        Usage:
            from app.models.user import User
            from app.utils.vietnamese_normalizer import create_normalization_listener
            
            create_normalization_listener(User, ['name', 'address'])
            # Now all User instances will auto-normalize these fields before insert/update
        
        Args:
            model_class: SQLAlchemy model class
            field_names: List of string field names to normalize
        """
        @event.listens_for(model_class, 'before_insert')
        @event.listens_for(model_class, 'before_update')
        def normalize_before_save(mapper, connection, target):
            normalize_model_fields(target, field_names)
    
except ImportError:
    # SQLAlchemy not available, skip listener setup
    pass


# ──────────────────────────────────────────────────────────────────────────
# 9. EXPORT PUBLIC API
# ──────────────────────────────────────────────────────────────────────────

__all__ = [
    'normalize_vietnamese_text',
    'is_normalized',
    'detect_normalization_form',
    'has_vietnamese_characters',
    'normalize_dict',
    'normalize_list',
    'normalize_pydantic_model',
    'analyze_text',
    'log_text_analysis',
    'get_normalized_text_dependency',
    'NormalizeVietnameseContext',
    'normalize_model_fields',
    'create_normalization_listener',
]
