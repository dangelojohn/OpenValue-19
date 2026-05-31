/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, onPatched, useRef } from "@odoo/owl";

/**
 * Renders a Plotly figure stored as a JSON string ({data, layout}) on a text
 * field. Replaces the legacy `web.AbstractField` widget removed in Odoo 17.
 */
export class PlotlyChartField extends Component {
    static template = "mrp_shop_floor_control.PlotlyChartField";
    static props = { ...standardFieldProps };

    setup() {
        this.chartRef = useRef("chart");
        onMounted(() => this.renderChart());
        onPatched(() => this.renderChart());
        onWillUnmount(() => this.purge());
    }

    get figure() {
        const raw = this.props.record.data[this.props.name];
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch {
            return null;
        }
    }

    purge() {
        const el = this.chartRef.el;
        if (el && window.Plotly) {
            window.Plotly.purge(el);
        }
    }

    renderChart() {
        const el = this.chartRef.el;
        if (!el || !window.Plotly) {
            return;
        }
        const figure = this.figure;
        if (!figure) {
            this.purge();
            el.replaceChildren();
            return;
        }
        window.Plotly.react(el, figure.data || [], figure.layout || {}, {
            displayModeBar: false,
            responsive: true,
        });
    }
}

export const plotlyChartField = {
    component: PlotlyChartField,
    supportedTypes: ["text"],
};

registry.category("fields").add("plotly_chart", plotlyChartField);
