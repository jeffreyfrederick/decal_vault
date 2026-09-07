from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

STATUS_ACTIVE = "active"
STATUS_DISCONTINUED = "discontinued"
STATUSES = (STATUS_ACTIVE, STATUS_DISCONTINUED)

# ISO 639-1 language codes, sorted by English name, for the decal Language
# dropdown. decal.language stores just the code (e.g. "EN").
LANGUAGES = (
    ("AB", "Abkhaz"),
    ("AA", "Afar"),
    ("AF", "Afrikaans"),
    ("AK", "Akan"),
    ("SQ", "Albanian"),
    ("AM", "Amharic"),
    ("AR", "Arabic"),
    ("AN", "Aragonese"),
    ("HY", "Armenian"),
    ("AS", "Assamese"),
    ("AV", "Avaric"),
    ("AE", "Avestan"),
    ("AY", "Aymara"),
    ("AZ", "Azerbaijani"),
    ("BM", "Bambara"),
    ("BA", "Bashkir"),
    ("EU", "Basque"),
    ("BE", "Belarusian"),
    ("BN", "Bengali"),
    ("BI", "Bislama"),
    ("BS", "Bosnian"),
    ("BR", "Breton"),
    ("BG", "Bulgarian"),
    ("MY", "Burmese"),
    ("CA", "Catalan"),
    ("CH", "Chamorro"),
    ("CE", "Chechen"),
    ("NY", "Chichewa"),
    ("ZH", "Chinese"),
    ("CU", "Church Slavic"),
    ("CV", "Chuvash"),
    ("KW", "Cornish"),
    ("CO", "Corsican"),
    ("CR", "Cree"),
    ("HR", "Croatian"),
    ("CS", "Czech"),
    ("DA", "Danish"),
    ("DV", "Divehi"),
    ("NL", "Dutch"),
    ("DZ", "Dzongkha"),
    ("EN", "English"),
    ("EO", "Esperanto"),
    ("ET", "Estonian"),
    ("EE", "Ewe"),
    ("FO", "Faroese"),
    ("FJ", "Fijian"),
    ("FI", "Finnish"),
    ("FR", "French"),
    ("FF", "Fulah"),
    ("GD", "Gaelic"),
    ("GL", "Galician"),
    ("LG", "Ganda"),
    ("KA", "Georgian"),
    ("DE", "German"),
    ("EL", "Greek"),
    ("KL", "Greenlandic"),
    ("GN", "Guarani"),
    ("GU", "Gujarati"),
    ("HT", "Haitian Creole"),
    ("HA", "Hausa"),
    ("HE", "Hebrew"),
    ("HZ", "Herero"),
    ("HI", "Hindi"),
    ("HO", "Hiri Motu"),
    ("HU", "Hungarian"),
    ("IS", "Icelandic"),
    ("IO", "Ido"),
    ("IG", "Igbo"),
    ("ID", "Indonesian"),
    ("IA", "Interlingua"),
    ("IE", "Interlingue"),
    ("IU", "Inuktitut"),
    ("IK", "Inupiaq"),
    ("GA", "Irish"),
    ("IT", "Italian"),
    ("JA", "Japanese"),
    ("JV", "Javanese"),
    ("KN", "Kannada"),
    ("KR", "Kanuri"),
    ("KS", "Kashmiri"),
    ("KK", "Kazakh"),
    ("KM", "Khmer"),
    ("KI", "Kikuyu"),
    ("RW", "Kinyarwanda"),
    ("KY", "Kirghiz"),
    ("KV", "Komi"),
    ("KG", "Kongo"),
    ("KO", "Korean"),
    ("KJ", "Kuanyama"),
    ("KU", "Kurdish"),
    ("LO", "Lao"),
    ("LA", "Latin"),
    ("LV", "Latvian"),
    ("LI", "Limburgan"),
    ("LN", "Lingala"),
    ("LT", "Lithuanian"),
    ("LU", "Luba-Katanga"),
    ("LB", "Luxembourgish"),
    ("MK", "Macedonian"),
    ("MG", "Malagasy"),
    ("MS", "Malay"),
    ("ML", "Malayalam"),
    ("MT", "Maltese"),
    ("GV", "Manx"),
    ("MI", "Maori"),
    ("MR", "Marathi"),
    ("MH", "Marshallese"),
    ("MN", "Mongolian"),
    ("NA", "Nauru"),
    ("NV", "Navajo"),
    ("ND", "Ndebele, North"),
    ("NR", "Ndebele, South"),
    ("NG", "Ndonga"),
    ("NE", "Nepali"),
    ("NO", "Norwegian"),
    ("NB", "Norwegian Bokmål"),
    ("NN", "Norwegian Nynorsk"),
    ("II", "Nuosu"),
    ("OC", "Occitan"),
    ("OJ", "Ojibwa"),
    ("OR", "Oriya"),
    ("OM", "Oromo"),
    ("OS", "Ossetian"),
    ("PI", "Pali"),
    ("PA", "Panjabi"),
    ("PS", "Pashto"),
    ("FA", "Persian"),
    ("PL", "Polish"),
    ("PT", "Portuguese"),
    ("QU", "Quechua"),
    ("RO", "Romanian"),
    ("RM", "Romansh"),
    ("RN", "Rundi"),
    ("RU", "Russian"),
    ("SE", "Sami, Northern"),
    ("SM", "Samoan"),
    ("SG", "Sango"),
    ("SA", "Sanskrit"),
    ("SC", "Sardinian"),
    ("SR", "Serbian"),
    ("SN", "Shona"),
    ("SD", "Sindhi"),
    ("SI", "Sinhala"),
    ("SK", "Slovak"),
    ("SL", "Slovenian"),
    ("SO", "Somali"),
    ("ST", "Sotho, Southern"),
    ("ES", "Spanish"),
    ("SU", "Sundanese"),
    ("SW", "Swahili"),
    ("SS", "Swati"),
    ("SV", "Swedish"),
    ("TL", "Tagalog"),
    ("TY", "Tahitian"),
    ("TG", "Tajik"),
    ("TA", "Tamil"),
    ("TT", "Tatar"),
    ("TE", "Telugu"),
    ("TH", "Thai"),
    ("BO", "Tibetan"),
    ("TI", "Tigrinya"),
    ("TO", "Tonga"),
    ("TS", "Tsonga"),
    ("TN", "Tswana"),
    ("TR", "Turkish"),
    ("TK", "Turkmen"),
    ("TW", "Twi"),
    ("UG", "Uighur"),
    ("UK", "Ukrainian"),
    ("UR", "Urdu"),
    ("UZ", "Uzbek"),
    ("VE", "Venda"),
    ("VI", "Vietnamese"),
    ("VO", "Volapük"),
    ("WA", "Walloon"),
    ("CY", "Welsh"),
    ("FY", "Western Frisian"),
    ("WO", "Wolof"),
    ("XH", "Xhosa"),
    ("YI", "Yiddish"),
    ("YO", "Yoruba"),
    ("ZA", "Zhuang"),
    ("ZU", "Zulu"),
)

# Fixed list, not free text. Add a new line here (and to app/icons.py's
# icon mapping) when Hunter ships a new equipment category.
CATEGORIES = (
    "Tire Changer",
    "Aligner",
    "Balancer",
    "Brake Lathe",
    "Lift Rack",
    "Inspection",
)

# Many-to-many: a decal applies to multiple models, normally, not as an
# edge case.
decal_models = db.Table(
    "decal_models",
    db.Column("decal_id", db.Integer, db.ForeignKey("decal.id"), primary_key=True),
    db.Column("equipment_model_id", db.Integer, db.ForeignKey("equipment_model.id"), primary_key=True),
)


class EquipmentModel(db.Model):
    """A specific model (e.g. 'TCX50') within an equipment category (e.g. 'Tire Changer')."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(120), nullable=False, index=True)

    __table_args__ = (db.UniqueConstraint("name", "category", name="uq_model_name_category"),)

    decals = db.relationship("Decal", secondary=decal_models, back_populates="models")

    def __repr__(self):
        return f"<EquipmentModel {self.category}/{self.name}>"


class Decal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.String(500))
    notes = db.Column(db.Text)
    image_filename = db.Column(db.String(255))
    # Original filename, kept for display only. image_filename above is a
    # generated UUID and is what's actually used on disk.
    original_filename = db.Column(db.String(255), nullable=True)

    language = db.Column(db.String(20), nullable=False, default="EN")
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE, index=True)
    # Optional qualifier (Adapter, Sensor, etc) for the decal as a whole -
    # applies across every model below, not just one of them.
    subcategory = db.Column(db.String(120), nullable=True)

    models = db.relationship("EquipmentModel", secondary=decal_models, back_populates="decals")

    # Optional pointer to the decal that replaced this one, when discontinued.
    superseded_by_id = db.Column(db.Integer, db.ForeignKey("decal.id"), nullable=True)
    superseded_by = db.relationship("Decal", remote_side=[id], foreign_keys=[superseded_by_id])

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Decal {self.part_number}>"
