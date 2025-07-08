# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PartnerMatchOrCreate(models.TransientModel):
    _name = "partner.match.or.create"
    _description = "Wizard to match/update an existing partner or create a new partner"

    res_model = fields.Char(required=True, readonly=True)
    res_id = fields.Integer(required=True, readonly=True)
    firstname = fields.Char()
    lastname = fields.Char(required=True)
    title_id = fields.Many2one("res.partner.title")
    email = fields.Char(string="E-mail")
    phone = fields.Char()
    mobile = fields.Char()
    street = fields.Char(string="Address Line 1")
    street2 = fields.Char(string="Address Line 2")
    zip = fields.Char(string="ZIP")
    city = fields.Char()
    country_id = fields.Many2one("res.country")
    update_partner_id = fields.Many2one("res.partner", string="Partner to Update")
    update_partner_email = fields.Char(
        related="update_partner_id.email", string="Current E-mail"
    )
    update_partner_phone = fields.Char(
        related="update_partner_id.phone", string="Current Phone"
    )
    update_partner_mobile = fields.Char(
        related="update_partner_id.mobile", string="Current Mobile"
    )
    # I can't use a related on update_partner_id because the full address
    # is not displayed any more when update_partner_id is changed
    update_partner_street = fields.Char(
        related="update_partner_id.street", string="Current Street"
    )
    update_partner_street2 = fields.Char(
        related="update_partner_id.street2", string="Current Street2"
    )
    update_partner_zip = fields.Char(
        related="update_partner_id.zip", string="Current ZIP"
    )
    update_partner_city = fields.Char(
        related="update_partner_id.city", string="Current City"
    )
    update_partner_country_id = fields.Many2one(
        related="update_partner_id.country_id", string="Current Country"
    )
    update_email = fields.Boolean(
        compute="_compute_update_bool",
        readonly=False,
        store=True,
        string="Update E-mail",
    )
    update_phone = fields.Boolean(
        compute="_compute_update_bool", readonly=False, store=True
    )
    update_mobile = fields.Boolean(
        compute="_compute_update_bool", readonly=False, store=True
    )
    update_address = fields.Boolean(
        compute="_compute_update_bool", readonly=False, store=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res_model = self._context.get("active_model")
        assert res_model
        res_id = self._context.get("active_id")
        assert res_id
        record = self.env[res_model].browse(res_id)
        # partner may have been created in the meantime
        update_partner = False
        if hasattr(record, "controller_email") and record.controller_email:
            update_partner = self.env["res.partner"].search(
                [("email", "=ilike", record.controller_email)], limit=1
            )
        res.update(
            {
                "res_model": res_model,
                "res_id": res_id,
                "update_partner_id": update_partner and update_partner.id or False,
            }
        )
        for rfield in [
            "firstname",
            "lastname",
            "title_id",
            "email",
            "phone",
            "mobile",
            "street",
            "street2",
            "zip",
            "city",
            "country_id",
        ]:
            controller_field = f"controller_{rfield}"
            if hasattr(record, controller_field):
                value = record[controller_field]
                if rfield == "email":
                    value = value and value.lower() or False
                res[rfield] = value
        return res

    def create_partner(self):
        self.ensure_one()
        rpo = self.env["res.partner"]
        vals = {
            "email": self.email,
            "phone": self.phone,
            "mobile": self.mobile,
            "street": self.street,
            "street2": self.street2,
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country_id.id or False,
            "title": self.title_id.id or False,
        }
        # if OCA module partner_firstname is installed
        if hasattr(rpo, "firstname") and hasattr(rpo, "lastname"):
            vals.update(
                {
                    "firstname": self.firstname,
                    "lastname": self.lastname,
                }
            )
        else:
            name = self.lastname
            if self.firstname:
                name = f"{self.firstname} {name}"
            vals["name"] = name
        partner = self.env["res.partner"].create(vals)
        model = self.env[self.res_model]
        partner.message_post(
            body=_("Partner created from %s web form.") % model._description
        )
        record = model.browse(self.res_id)
        record.write({"partner_id": partner.id})
        record.message_post(
            body=_(
                "Partner <a href=# data-oe-model=res.partner data-oe-id=%(partner_id)d>"
                "%(partner_name)s</a> created from web form information.",
                partner_id=partner.id,
                partner_name=partner.display_name,
            )
        )
        action = {
            "type": "ir.actions.act_window",
            "name": _("New Partner"),
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": partner.id,
        }
        return action

    @api.depends("update_partner_id")
    def _compute_update_bool(self):
        for wiz in self:
            update_email = False
            update_phone = False
            update_mobile = False
            update_address = False
            if wiz.update_partner_id:
                if wiz.email and wiz.email != wiz.update_partner_id.email:
                    update_email = True
                if wiz.phone and wiz.phone != wiz.update_partner_id.phone:
                    update_phone = True
                if wiz.mobile and wiz.mobile != wiz.update_partner_id.mobile:
                    update_mobile = True
                if wiz.street and wiz.city and wiz.zip and wiz.country_id:
                    update_address = True
            wiz.update_email = update_email
            wiz.update_phone = update_phone
            wiz.update_mobile = update_mobile
            wiz.update_address = update_address

    def update_partner(self):
        self.ensure_one()
        if not self.update_partner_id:
            raise UserError(_("The partner to update is not set."))
        vals = {}
        if self.update_phone:
            vals["phone"] = self.phone
        if self.update_mobile:
            vals["mobile"] = self.mobile
        if self.update_email:
            vals["email"] = self.email
        if self.update_address:
            vals.update(
                {
                    "street": self.street,
                    "street2": self.street2,
                    "zip": self.zip,
                    "city": self.city,
                    "country_id": self.country_id.id or False,
                }
            )
        model = self.env[self.res_model]
        if vals:
            self.update_partner_id.write(vals)
            # TODO improve message generation + add address
            self.update_partner_id.message_post(
                body=_(
                    "Partner e-mail and/or phone and/or mobile updated from %s web form."
                )
                % model._description
            )
        record = model.browse(self.res_id)
        record.write({"partner_id": self.update_partner_id.id})
        record.message_post(
            body=_("Partner updated from %s web form.") % model._description
        )
