# -*- coding: utf-8 -*-
import datetime as dt
from comport.database import (
    Column,
    db,
    Model,
    ReferenceCol,
    relationship,
    SurrogatePK,
)
from comport.charts.models import ChartBlockDefaults

from flask import current_app

from comport.user.models import User, Role

class Department(SurrogatePK, Model):
    __tablename__ = 'departments'
    id = Column(db.Integer, primary_key=True, index=True)
    name = Column(db.String(80), unique=True, nullable=False)
    invite_codes = relationship("Invite_Code", backref="department")
    users = relationship("User", backref="department")
    use_of_force_incidents = relationship("UseOfForceIncident", backref="department")
    blocks = relationship("ChartBlock", backref="department")

    def get_uof_blocks(self):
        return dict([(block.slug, block) for block in self.blocks if block.dataset == "Use of Force"])

    def get_extractor(self):
        extractors = list(filter(lambda u: u.type == "extractors" ,self.users))
        return extractors[0] if extractors else None

    def __init__(self, name, **kwargs):
        db.Model.__init__(self, name=name, **kwargs)
        for default_chart_block in ChartBlockDefaults.query.all():
            self.blocks.append(default_chart_block.make_real_block())

    def __repr__(self):
        return '<Department({name})>'.format(name=self.name)

    def get_uof_csv(self):
        csv = "id,occuredDate,division,precinct,shift,beat,disposition,censusTract,officerForceType,residentResistType,officerWeaponUsed,residentWeaponUsed,serviceType,arrestMade,arrestCharges,residentInjured,residentHospitalized,officerInjured,officerHospitalized,useOfForceReason,residentRace,officerRace,officerIdentifier\n"
        use_of_force_incidents = self.use_of_force_incidents
        for incident in use_of_force_incidents:
            csv += incident.to_csv_row()
        return csv

class Extractor(User):
    __tablename__ = 'extractors'
    id = Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    next_month = Column(db.Integer)
    next_year = Column(db.Integer)

    __mapper_args__ = {
        'polymorphic_identity':'extractors',
        'inherit_condition': (id==User.id)
    }

    def generate_envs(self, password):
        return """
            COMPORT_BASE_URL="%s"
            COMPORT_USERNAME="%s"
            COMPORT_PASSWORD="%s"
            COMPORT_DEPARTMENT_ID="%s"
            COMPORT_SQL_SERVER_URL =
            COMPORT_SQL_SERVER_DATABASE =
            COMPORT_SQL_SERVER_USERNAME =
            COMPORT_SQL_SERVER_PASSWORD =
        """ % (current_app.config["BASE_URL"], self.username, password, self.department_id,)

    def from_department_and_password(department, password):
        extractor = Extractor.create(username='%s-extractor' % department.name.replace (" ", "_"), email='extractor@example.com', department_id=department.id, password=password)
        extractor.roles.append(Role.create(name="extractor"))
        extractor.save()

        envs = extractor.generate_envs(password)

        return (extractor,envs)
