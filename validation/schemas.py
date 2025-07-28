"""
Pydantic validation schemas for MCP freight system.
Provides comprehensive data validation models with automatic type checking.
"""

import re
from typing import Optional, List, Union, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, validator, EmailStr, root_validator
from pydantic.types import PositiveFloat, PositiveInt, constr

from .validators import (
    FreightValidator, AddressValidator, DocumentValidator, 
    UserValidator, FileValidator, ValidationError
)


class FreightTypeEnum(str, Enum):
    """Enum for freight types."""
    EXPRESS = "express"
    STANDARD = "standard"
    ECONOMIC = "economic"
    HEAVY = "heavy"
    FRAGILE = "fragile"
    DANGEROUS = "dangerous"


class StateEnum(str, Enum):
    """Enum for Brazilian states."""
    AC = "AC"
    AL = "AL"
    AP = "AP"
    AM = "AM"
    BA = "BA"
    CE = "CE"
    DF = "DF"
    ES = "ES"
    GO = "GO"
    MA = "MA"
    MT = "MT"
    MS = "MS"
    MG = "MG"
    PA = "PA"
    PB = "PB"
    PR = "PR"
    PE = "PE"
    PI = "PI"
    RJ = "RJ"
    RN = "RN"
    RS = "RS"
    RO = "RO"
    RR = "RR"
    SC = "SC"
    SP = "SP"
    SE = "SE"
    TO = "TO"


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    class Config:
        # Validate assignment to prevent malicious data injection
        validate_assignment = True
        # Allow extra fields but validate them
        extra = "forbid"
        # Use enum values instead of names
        use_enum_values = True
        # Validate default values
        validate_all = True
        # Allow population by field name or alias
        allow_population_by_field_name = True


class AddressSchema(BaseSchema):
    """Schema for address validation."""
    
    street: constr(min_length=5, max_length=200, regex=r'^[a-zA-Z0-9\s\.,\-\/\#]+$') = Field(
        ..., 
        description="Street address",
        example="Rua das Flores, 123"
    )
    
    number: constr(min_length=1, max_length=10, regex=r'^[a-zA-Z0-9\-\/]+$') = Field(
        ..., 
        description="Address number",
        example="123A"
    )
    
    complement: Optional[constr(max_length=100, regex=r'^[a-zA-Z0-9\s\.,\-\/\#]*$')] = Field(
        None, 
        description="Address complement",
        example="Apto 101"
    )
    
    neighborhood: constr(min_length=2, max_length=100, regex=r'^[a-zA-ZÀ-ÿ\s\-\']+$') = Field(
        ..., 
        description="Neighborhood",
        example="Centro"
    )
    
    city: constr(min_length=2, max_length=100, regex=r'^[a-zA-ZÀ-ÿ\s\-\']+$') = Field(
        ..., 
        description="City name",
        example="São Paulo"
    )
    
    state: StateEnum = Field(
        ..., 
        description="Brazilian state code",
        example="SP"
    )
    
    cep: constr(regex=r'^\d{5}-?\d{3}$') = Field(
        ..., 
        description="Brazilian postal code",
        example="01234-567"
    )
    
    @validator('cep')
    def validate_cep(cls, v):
        """Validate CEP format and check digits."""
        validator = AddressValidator()
        try:
            validator.validate_cep(v, 'cep')
        except ValidationError as e:
            raise ValueError(e.message)
        return v
    
    @validator('street', 'neighborhood', 'city')
    def validate_no_sql_injection(cls, v, field):
        """Check for SQL injection attempts."""
        validator = AddressValidator()
        try:
            validator.check_sql_injection(v, field.name)
            validator.check_xss(v, field.name)
        except ValidationError as e:
            raise ValueError(e.message)
        return v


class FreightQuoteSchema(BaseSchema):
    """Schema for freight quote requests."""
    
    origin_address: AddressSchema = Field(
        ..., 
        description="Origin address"
    )
    
    destination_address: AddressSchema = Field(
        ..., 
        description="Destination address"
    )
    
    weight: PositiveFloat = Field(
        ..., 
        gt=0.1, 
        le=30000, 
        description="Package weight in kg",
        example=1.5
    )
    
    length: PositiveFloat = Field(
        ..., 
        gt=1, 
        le=500, 
        description="Package length in cm",
        example=30.0
    )
    
    width: PositiveFloat = Field(
        ..., 
        gt=1, 
        le=500, 
        description="Package width in cm",
        example=20.0
    )
    
    height: PositiveFloat = Field(
        ..., 
        gt=1, 
        le=500, 
        description="Package height in cm",
        example=10.0
    )
    
    freight_type: FreightTypeEnum = Field(
        FreightTypeEnum.STANDARD, 
        description="Type of freight service",
        example="standard"
    )
    
    declared_value: Optional[PositiveFloat] = Field(
        None, 
        description="Declared value for insurance",
        example=100.00
    )
    
    additional_services: Optional[List[str]] = Field(
        None, 
        description="Additional services requested",
        example=["insurance", "tracking"]
    )
    
    @validator('weight', 'length', 'width', 'height')
    def validate_dimensions(cls, v, field):
        """Validate package dimensions."""
        validator = FreightValidator()
        try:
            if field.name == 'weight':
                validator.validate_weight(v, field.name)
            else:
                # For dimensions, pass a dummy set since we're validating individual values
                validator.validate_dimensions(v, v, v, field.name)
        except ValidationError as e:
            raise ValueError(e.message)
        return v
    
    @root_validator
    def validate_dimensions_together(cls, values):
        """Validate dimensions as a group."""
        length = values.get('length')
        width = values.get('width') 
        height = values.get('height')
        
        if all([length, width, height]):
            validator = FreightValidator()
            try:
                validator.validate_dimensions(length, width, height, 'dimensions')
            except ValidationError as e:
                raise ValueError(e.message)
        
        return values
    
    @validator('additional_services')
    def validate_additional_services(cls, v):
        """Validate additional services list."""
        if v:
            allowed_services = [
                'insurance', 'tracking', 'receipt', 'express_delivery',
                'fragile_handling', 'signature_required', 'weekend_delivery'
            ]
            for service in v:
                if service not in allowed_services:
                    raise ValueError(f"Invalid service: {service}")
        return v


class UserSchema(BaseSchema):
    """Schema for user registration and profile."""
    
    name: constr(min_length=2, max_length=100, regex=r'^[a-zA-ZÀ-ÿ\s\-\']+$') = Field(
        ..., 
        description="Full name",
        example="João Silva"
    )
    
    email: EmailStr = Field(
        ..., 
        description="Email address",
        example="joao@example.com"
    )
    
    phone: constr(regex=r'^\(?\d{2}\)?\s?9?\d{4}-?\d{4}$') = Field(
        ..., 
        description="Phone number",
        example="(11) 99999-9999"
    )
    
    cpf: Optional[constr(regex=r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$')] = Field(
        None, 
        description="Brazilian CPF",
        example="123.456.789-00"
    )
    
    cnpj: Optional[constr(regex=r'^\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}$')] = Field(
        None, 
        description="Brazilian CNPJ",
        example="12.345.678/0001-90"
    )
    
    password: Optional[constr(min_length=8, max_length=128)] = Field(
        None, 
        description="Password (for registration)",
        example="SecurePass123!"
    )
    
    company_name: Optional[constr(max_length=200)] = Field(
        None, 
        description="Company name (if applicable)",
        example="Empresa LTDA"
    )
    
    address: Optional[AddressSchema] = Field(
        None, 
        description="User address"
    )
    
    @validator('email')
    def validate_email_security(cls, v):
        """Additional email validation for security."""
        validator = UserValidator()
        try:
            validator.validate_email(v, 'email')
        except ValidationError as e:
            raise ValueError(e.message)
        return v
    
    @validator('phone')
    def validate_phone_format(cls, v):
        """Validate phone number format."""
        validator = UserValidator()
        try:
            validator.validate_phone(v, 'phone')
        except ValidationError as e:
            raise ValueError(e.message)
        return v
    
    @validator('cpf')
    def validate_cpf_digits(cls, v):
        """Validate CPF check digits."""
        if v:
            validator = DocumentValidator()
            try:
                validator.validate_cpf(v, 'cpf')
            except ValidationError as e:
                raise ValueError(e.message)
        return v
    
    @validator('cnpj')
    def validate_cnpj_digits(cls, v):
        """Validate CNPJ check digits."""
        if v:
            validator = DocumentValidator()
            try:
                validator.validate_cnpj(v, 'cnpj')
            except ValidationError as e:
                raise ValueError(e.message)
        return v
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if v:
            validator = UserValidator()
            try:
                validator.validate_password(v, 'password')
            except ValidationError as e:
                raise ValueError(e.message)
        return v
    
    @validator('name', 'company_name')
    def validate_no_malicious_content(cls, v, field):
        """Check for malicious content."""
        if v:
            validator = UserValidator()
            try:
                validator.check_sql_injection(v, field.name)
                validator.check_xss(v, field.name)
            except ValidationError as e:
                raise ValueError(e.message)
        return v
    
    @root_validator
    def validate_document_requirement(cls, values):
        """Ensure at least one document (CPF or CNPJ) is provided."""
        cpf = values.get('cpf')
        cnpj = values.get('cnpj')
        
        if not cpf and not cnpj:
            raise ValueError("Either CPF or CNPJ must be provided")
        
        if cpf and cnpj:
            raise ValueError("Provide either CPF or CNPJ, not both")
        
        return values


class DocumentSchema(BaseSchema):
    """Schema for document upload."""
    
    document_type: constr(regex=r'^(cpf|cnpj|rg|passport|license)$') = Field(
        ..., 
        description="Type of document",
        example="cpf"
    )
    
    document_number: constr(min_length=5, max_length=50) = Field(
        ..., 
        description="Document number",
        example="123.456.789-00"
    )
    
    filename: constr(min_length=1, max_length=255) = Field(
        ..., 
        description="Original filename",
        example="document.pdf"
    )
    
    description: Optional[constr(max_length=500)] = Field(
        None, 
        description="Document description",
        example="Copy of CPF document"
    )
    
    @validator('filename')
    def validate_filename_security(cls, v):
        """Validate filename for security."""
        validator = FileValidator()
        try:
            validator.validate_file_extension(v, 'filename')
        except ValidationError as e:
            raise ValueError(e.message)
        return v
    
    @validator('document_number')
    def validate_document_number(cls, v, values):
        """Validate document number based on type."""
        document_type = values.get('document_type')
        
        if document_type == 'cpf':
            validator = DocumentValidator()
            try:
                validator.validate_cpf(v, 'document_number')
            except ValidationError as e:
                raise ValueError(e.message)
        elif document_type == 'cnpj':
            validator = DocumentValidator()
            try:
                validator.validate_cnpj(v, 'document_number')
            except ValidationError as e:
                raise ValueError(e.message)
        
        return v


class FileUploadSchema(BaseSchema):
    """Schema for file upload validation."""
    
    filename: constr(min_length=1, max_length=255) = Field(
        ..., 
        description="Filename",
        example="document.pdf"
    )
    
    content_type: constr(max_length=100) = Field(
        ..., 
        description="MIME type",
        example="application/pdf"
    )
    
    file_size: PositiveInt = Field(
        ..., 
        le=10485760,  # 10MB
        description="File size in bytes",
        example=1024000
    )
    
    category: Optional[constr(regex=r'^(document|image|invoice|receipt)$')] = Field(
        None, 
        description="File category",
        example="document"
    )
    
    @validator('filename')
    def validate_filename_extension(cls, v):
        """Validate filename and extension."""
        validator = FileValidator()
        try:
            validator.validate_file_extension(v, 'filename')
        except ValidationError as e:
            raise ValueError(e.message)
        return v
    
    @validator('content_type')
    def validate_mime_type(cls, v):
        """Validate MIME type."""
        validator = FileValidator()
        try:
            validator.validate_mime_type(v, 'content_type')
        except ValidationError as e:
            raise ValueError(e.message)
        return v
    
    @validator('file_size')
    def validate_file_size_limit(cls, v):
        """Validate file size."""
        validator = FileValidator()
        try:
            validator.validate_file_size(v, 'file_size')
        except ValidationError as e:
            raise ValueError(e.message)
        return v


class FreightTrackingSchema(BaseSchema):
    """Schema for freight tracking requests."""
    
    tracking_code: constr(min_length=5, max_length=50, regex=r'^[A-Z0-9\-]+$') = Field(
        ..., 
        description="Tracking code",
        example="FR123456789BR"
    )
    
    @validator('tracking_code')
    def validate_tracking_code_security(cls, v):
        """Validate tracking code for security."""
        validator = FreightValidator()
        try:
            validator.check_sql_injection(v, 'tracking_code')
            validator.check_xss(v, 'tracking_code')
        except ValidationError as e:
            raise ValueError(e.message)
        return v


class FreightOrderSchema(BaseSchema):
    """Schema for freight order creation."""
    
    quote_id: Optional[constr(min_length=1, max_length=50)] = Field(
        None, 
        description="Quote ID reference",
        example="quote_123456"
    )
    
    freight_quote: FreightQuoteSchema = Field(
        ..., 
        description="Freight quote details"
    )
    
    sender: UserSchema = Field(
        ..., 
        description="Sender information"
    )
    
    recipient: UserSchema = Field(
        ..., 
        description="Recipient information"
    )
    
    invoice_value: Optional[PositiveFloat] = Field(
        None, 
        description="Invoice value",
        example=150.00
    )
    
    pickup_date: Optional[date] = Field(
        None, 
        description="Preferred pickup date",
        example="2024-01-15"
    )
    
    delivery_instructions: Optional[constr(max_length=1000)] = Field(
        None, 
        description="Special delivery instructions",
        example="Call before delivery"
    )
    
    @validator('pickup_date')
    def validate_pickup_date(cls, v):
        """Validate pickup date is not in the past."""
        if v and v < date.today():
            raise ValueError("Pickup date cannot be in the past")
        return v
    
    @validator('delivery_instructions')
    def validate_delivery_instructions_security(cls, v):
        """Validate delivery instructions for security."""
        if v:
            validator = FreightValidator()
            try:
                validator.check_sql_injection(v, 'delivery_instructions')
                validator.check_xss(v, 'delivery_instructions')
            except ValidationError as e:
                raise ValueError(e.message)
        return v


class APIResponseSchema(BaseSchema):
    """Schema for API responses."""
    
    success: bool = Field(
        ..., 
        description="Request success status",
        example=True
    )
    
    data: Optional[Any] = Field(
        None, 
        description="Response data"
    )
    
    message: Optional[str] = Field(
        None, 
        description="Response message",
        example="Operation completed successfully"
    )
    
    errors: Optional[List[str]] = Field(
        None, 
        description="List of errors",
        example=[]
    )
    
    metadata: Optional[dict] = Field(
        None, 
        description="Additional metadata"
    )


class PaginationSchema(BaseSchema):
    """Schema for paginated responses."""
    
    page: PositiveInt = Field(
        1, 
        description="Current page number",
        example=1
    )
    
    per_page: PositiveInt = Field(
        10, 
        le=100,
        description="Items per page",
        example=10
    )
    
    total_items: Optional[int] = Field(
        None, 
        description="Total number of items",
        example=150
    )
    
    total_pages: Optional[int] = Field(
        None, 
        description="Total number of pages",
        example=15
    )