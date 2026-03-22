<?php
/**
 * Plugin Name: Europamundo Circuitos
 * Description: Registra el CPT "Circuito" y taxonomías para programas de viaje Europamundo.
 * Version: 1.0
 * Author: Gina Travel
 */

// ══════════════════════════════════════════════════════
// CUSTOM POST TYPE: CIRCUITO
// ══════════════════════════════════════════════════════

function europamundo_register_cpt() {
    register_post_type('circuito', array(
        'labels' => array(
            'name'               => 'Circuitos',
            'singular_name'      => 'Circuito',
            'menu_name'          => 'Circuitos',
            'add_new'            => 'Añadir Circuito',
            'add_new_item'       => 'Añadir Nuevo Circuito',
            'edit_item'          => 'Editar Circuito',
            'new_item'           => 'Nuevo Circuito',
            'view_item'          => 'Ver Circuito',
            'search_items'       => 'Buscar Circuitos',
            'not_found'          => 'No se encontraron circuitos',
            'all_items'          => 'Todos los Circuitos',
        ),
        'public'             => true,
        'has_archive'        => true,
        'rewrite'            => array('slug' => 'circuitos', 'with_front' => false),
        'menu_icon'          => 'dashicons-airplane',
        'supports'           => array('title', 'editor', 'thumbnail', 'custom-fields'),  // sin 'author'
        'show_in_rest'       => true,  // Habilita REST API + Gutenberg
        'taxonomies'         => array('region_europamundo', 'serie_europamundo'),
    ));
}
add_action('init', 'europamundo_register_cpt');

// ══════════════════════════════════════════════════════
// TAXONOMÍA: REGIÓN
// ══════════════════════════════════════════════════════

function europamundo_register_region_taxonomy() {
    register_taxonomy('region_europamundo', 'circuito', array(
        'labels' => array(
            'name'          => 'Regiones',
            'singular_name' => 'Región',
            'menu_name'     => 'Regiones',
            'all_items'     => 'Todas las Regiones',
            'edit_item'     => 'Editar Región',
            'add_new_item'  => 'Añadir Región',
            'search_items'  => 'Buscar Regiones',
        ),
        'hierarchical'   => true,   // como categorías (con padre/hijo)
        'public'         => true,
        'show_in_rest'   => true,   // REST API
        'rewrite'        => array('slug' => 'circuitos/region', 'with_front' => false),
        'show_admin_column' => true,
    ));
}
add_action('init', 'europamundo_register_region_taxonomy');

// ══════════════════════════════════════════════════════
// TAXONOMÍA: SERIE
// ══════════════════════════════════════════════════════

function europamundo_register_serie_taxonomy() {
    register_taxonomy('serie_europamundo', 'circuito', array(
        'labels' => array(
            'name'          => 'Series',
            'singular_name' => 'Serie',
            'menu_name'     => 'Series',
            'all_items'     => 'Todas las Series',
            'edit_item'     => 'Editar Serie',
            'add_new_item'  => 'Añadir Serie',
            'search_items'  => 'Buscar Series',
        ),
        'hierarchical'   => true,
        'public'         => true,
        'show_in_rest'   => true,
        'rewrite'        => array('slug' => 'circuitos/serie', 'with_front' => false),
        'show_admin_column' => true,
    ));
}
add_action('init', 'europamundo_register_serie_taxonomy');

// ══════════════════════════════════════════════════════
// REGISTRAR META FIELDS PARA REST API
// ══════════════════════════════════════════════════════

function europamundo_register_meta_fields() {
    $meta_fields = array(
        'id_europamundo',
        'precio_desde',
        'dias',
        'fechas_salida',
    );

    foreach ($meta_fields as $field) {
        register_post_meta('circuito', $field, array(
            'type'          => 'string',
            'single'        => true,
            'show_in_rest'  => true,
        ));
    }
}

// ══════════════════════════════════════════════════════
// ENDPOINT REST API PARA SETEAR RANK MATH SEO META
// ══════════════════════════════════════════════════════

function europamundo_register_seo_endpoint() {
    register_rest_route('europamundo/v1', '/seo/(?P<id>\d+)', array(
        'methods'             => 'POST',
        'callback'            => 'europamundo_update_seo_meta',
        'permission_callback' => function() {
            return current_user_can('edit_posts');
        },
        'args' => array(
            'id' => array('type' => 'integer', 'required' => true),
        ),
    ));
}
add_action('rest_api_init', 'europamundo_register_seo_endpoint');

function europamundo_update_seo_meta($request) {
    $post_id = $request['id'];
    $params = $request->get_json_params();

    if (!get_post($post_id)) {
        return new WP_Error('not_found', 'Post not found', array('status' => 404));
    }

    $seo_fields = array(
        'rank_math_title',
        'rank_math_description',
        'rank_math_focus_keyword',
        'rank_math_facebook_title',
        'rank_math_facebook_description',
        'rank_math_twitter_title',
        'rank_math_twitter_description',
    );

    $updated = array();
    foreach ($seo_fields as $field) {
        if (isset($params[$field])) {
            update_post_meta($post_id, $field, sanitize_text_field($params[$field]));
            $updated[$field] = true;
        }
    }

    return array('success' => true, 'updated' => $updated, 'post_id' => $post_id);
}
add_action('init', 'europamundo_register_meta_fields');

// ══════════════════════════════════════════════════════
// CREAR REGIONES POR DEFECTO AL ACTIVAR EL PLUGIN
// ══════════════════════════════════════════════════════

function europamundo_create_default_terms() {
    $regiones = array(
        'USA y Canadá',
        'México y Cuba',
        'China, Corea y Japón',
        'India y Oceanía',
        'Oriente Medio y África',
        'Península Ibérica y Marruecos',
        'Europa Mediterránea',
        'Europa Atlántica',
        'Europa Nórdica',
        'Europa Central',
    );

    foreach ($regiones as $region) {
        if (!term_exists($region, 'region_europamundo')) {
            wp_insert_term($region, 'region_europamundo');
        }
    }

    $series = array(
        'Regular',
        'Más Incluido',
        'Turista',
        'Cruceros Fluviales',
    );

    foreach ($series as $serie) {
        if (!term_exists($serie, 'serie_europamundo')) {
            wp_insert_term($serie, 'serie_europamundo');
        }
    }
}
register_activation_hook(__FILE__, 'europamundo_create_default_terms');

// ══════════════════════════════════════════════════════
// CREAR MENÚ DE NAVEGACIÓN
// ══════════════════════════════════════════════════════

function europamundo_create_menu() {
    // Buscar el menú "Inicio" (nombre del menú del sitio)
    $menu_obj = wp_get_nav_menu_object('Inicio');
    if (!$menu_obj) {
        // Fallback: buscar cualquier menú asignado
        $locations = get_nav_menu_locations();
        if (empty($locations)) return;
        $menu_id = reset($locations);
    } else {
        $menu_id = $menu_obj->term_id;
    }

    // Verificar si ya agregamos nuestro menú (evitar duplicados)
    $items = wp_get_nav_menu_items($menu_id);
    if ($items) {
        foreach ($items as $item) {
            if ($item->title === 'Circuitos Europamundo') {
                return; // ya existe
            }
        }
    }

    // Buscar "Salidas Regulares" para anidar dentro
    $parent_id = 0;
    if ($items) {
        foreach ($items as $item) {
            if ($item->title === 'Salidas Regulares') {
                $parent_id = $item->ID;
                break;
            }
        }
    }

    // Crear "Circuitos Europamundo" como submenú de Salidas Regulares (o al root si no existe)
    $europamundo_id = wp_update_nav_menu_item($menu_id, 0, array(
        'menu-item-title'     => 'Circuitos Europamundo',
        'menu-item-url'       => home_url('/circuitos/'),
        'menu-item-status'    => 'publish',
        'menu-item-type'      => 'custom',
        'menu-item-parent-id' => $parent_id,
    ));

    // Crear sub-ítems por cada región
    $regiones = get_terms(array(
        'taxonomy'   => 'region_europamundo',
        'hide_empty' => false,
        'orderby'    => 'name',
    ));

    if (!is_wp_error($regiones)) {
        foreach ($regiones as $region) {
            wp_update_nav_menu_item($menu_id, 0, array(
                'menu-item-title'     => $region->name,
                'menu-item-url'       => get_term_link($region),
                'menu-item-status'    => 'publish',
                'menu-item-type'      => 'custom',
                'menu-item-parent-id' => $europamundo_id,
            ));
        }
    }
}

// ══════════════════════════════════════════════════════
// OCULTAR AUTOR EN CIRCUITOS (frontend)
// ══════════════════════════════════════════════════════

function europamundo_custom_styles() {
    ?>
    <style>
    /* Ocultar autor en circuitos */
    .single-circuito .author-box,
    .single-circuito .post-author,
    .single-circuito .entry-author,
    .single-circuito .author-info,
    .single-circuito .single-post-author { display: none !important; }

    /* ===== Elementor HFE Nav Menu - Fix dropdown ===== */
    .elementor-1923 .elementor-element.elementor-element-94deac2 .sub-menu li a.hfe-sub-menu-item,
    .elementor-1923 .elementor-element.elementor-element-94deac2 nav.hfe-dropdown li a.hfe-sub-menu-item,
    .elementor-1923 .elementor-element.elementor-element-94deac2 nav.hfe-dropdown li a.hfe-menu-item,
    .elementor-1923 .elementor-element.elementor-element-94deac2 nav.hfe-dropdown-expandible li a.hfe-menu-item,
    .elementor-1923 .elementor-element.elementor-element-94deac2 nav.hfe-dropdown-expandible li a.hfe-sub-menu-item {
        font-size: 14px !important;
        font-weight: 400 !important;
        font-family: Roboto, sans-serif !important;
        color: #3b3d42 !important;
        padding: 10px 18px !important;
        line-height: 1.5 !important;
        background: #fff !important;
    }

    .elementor-1923 .elementor-element.elementor-element-94deac2 .sub-menu li a.hfe-sub-menu-item:hover,
    .elementor-1923 .elementor-element.elementor-element-94deac2 nav.hfe-dropdown li a.hfe-sub-menu-item:hover {
        color: #398ffc !important;
        background: #f0f7ff !important;
    }

    .elementor-1923 .elementor-element.elementor-element-94deac2 .sub-menu {
        min-width: 260px !important;
        width: max-content !important;
        max-width: 350px !important;
    }

    .elementor-1923 .elementor-element.elementor-element-94deac2 .sub-menu .hfe-menu-toggle {
        float: right !important;
    }
    </style>
    <?php
}
add_action('wp_footer', 'europamundo_custom_styles');

// ══════════════════════════════════════════════════════
// SHORTCODE: [europamundo_circuitos]
// ══════════════════════════════════════════════════════

function europamundo_circuitos_shortcode($atts) {
    $atts = shortcode_atts(array(
        'region'   => '',
        'serie'    => '',
        'limit'    => 50,
        'columns'  => 3,
        'min_dias' => '',
        'max_dias' => '',
    ), $atts);

    $args = array(
        'post_type'      => 'circuito',
        'posts_per_page' => intval($atts['limit']),
        'post_status'    => 'publish',
        'orderby'        => 'title',
        'order'          => 'ASC',
    );

    // Filtrar por taxonomía
    $tax_query = array();
    if (!empty($atts['region'])) {
        $tax_query[] = array(
            'taxonomy' => 'region_europamundo',
            'field'    => 'slug',
            'terms'    => $atts['region'],
        );
    }
    if (!empty($atts['serie'])) {
        $tax_query[] = array(
            'taxonomy' => 'serie_europamundo',
            'field'    => 'slug',
            'terms'    => $atts['serie'],
        );
    }
    if (!empty($tax_query)) {
        $args['tax_query'] = $tax_query;
    }

    // Filtro por duración (días)
    $meta_query = array();
    if (!empty($atts['min_dias'])) {
        $meta_query[] = array(
            'key'     => 'dias',
            'value'   => intval($atts['min_dias']),
            'compare' => '>=',
            'type'    => 'NUMERIC',
        );
    }
    if (!empty($atts['max_dias'])) {
        $meta_query[] = array(
            'key'     => 'dias',
            'value'   => intval($atts['max_dias']),
            'compare' => '<=',
            'type'    => 'NUMERIC',
        );
    }
    if (!empty($meta_query)) {
        $args['meta_query'] = $meta_query;
    }

    $query = new WP_Query($args);

    if (!$query->have_posts()) {
        return '<p style="text-align:center;color:#999;">No se encontraron circuitos.</p>';
    }

    $cols = intval($atts['columns']);
    $wa_link = 'https://wa.link/pe2cih';

    $html = '<style>
    .emc-grid { display:grid; grid-template-columns:repeat(' . $cols . ',1fr); gap:24px; max-width:1200px; margin:0 auto; }
    @media(max-width:900px) { .emc-grid { grid-template-columns:repeat(2,1fr); } }
    @media(max-width:600px) { .emc-grid { grid-template-columns:1fr; } }
    .emc-card { background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.08); transition:transform 0.2s,box-shadow 0.2s; display:flex; flex-direction:column; }
    .emc-card:hover { transform:translateY(-4px); box-shadow:0 8px 24px rgba(0,0,0,0.12); }
    .emc-card-img { position:relative; height:220px; background:linear-gradient(135deg,#398ffc 0%,#1a6fdc 100%); overflow:hidden; }
    .emc-card-img img { width:100%; height:100%; object-fit:cover; }
    .emc-badge { position:absolute; bottom:60px; left:0; background:rgba(0,0,0,0.7); color:#fff; padding:4px 12px; font-size:12px; border-radius:0 6px 6px 0; }
    .emc-badge strong { font-size:20px; font-weight:800; }
    .emc-badge small { font-size:11px; opacity:0.8; margin-left:4px; }
    .emc-wa-btn { position:absolute; bottom:12px; left:50%; transform:translateX(-50%); background:#25D366; color:#fff; border:none; border-radius:20px; padding:8px 20px; font-size:12px; font-weight:600; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; gap:6px; white-space:nowrap; transition:background 0.2s; }
    .emc-wa-btn:hover { background:#1da851; color:#fff; }
    .emc-wa-btn svg { width:16px; height:16px; fill:#fff; }
    .emc-card-body { padding:16px 20px; flex:1; display:flex; flex-direction:column; text-align:center; }
    .emc-card-region { font-size:11px; color:#398ffc; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; }
    .emc-card-title { font-size:18px; font-weight:700; color:#398ffc; line-height:1.3; margin-bottom:10px; min-height:44px; }
    .emc-card-title a { color:#398ffc; text-decoration:none; }
    .emc-card-title a:hover { color:#1a6fdc; }
    .emc-card-meta { font-size:13px; color:#888; margin-bottom:6px; }
    .emc-card-services { display:flex; justify-content:center; gap:12px; font-size:11px; color:#999; margin:8px 0 14px; flex-wrap:wrap; }
    .emc-card-services span { display:inline-flex; align-items:center; gap:4px; }
    .emc-card-btn { display:inline-block; background:#398ffc; color:#fff; border-radius:20px; padding:10px 28px; font-size:13px; font-weight:700; text-decoration:none; transition:background 0.2s; margin-top:auto; align-self:center; }
    .emc-card-btn:hover { background:#1a6fdc; color:#fff; }
    </style>';

    $html .= '<div class="emc-grid">';

    $wa_svg = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492l4.572-1.467A11.94 11.94 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818c-2.17 0-4.182-.614-5.899-1.673l-.423-.253-2.71.869.881-2.627-.277-.441A9.777 9.777 0 012.182 12c0-5.415 4.403-9.818 9.818-9.818S21.818 6.585 21.818 12s-4.403 9.818-9.818 9.818z"/></svg>';

    while ($query->have_posts()) {
        $query->the_post();
        $post_id = get_the_ID();

        $precio   = get_post_meta($post_id, 'precio_desde', true);
        $dias     = get_post_meta($post_id, 'dias', true);
        $fechas   = get_post_meta($post_id, 'fechas_salida', true);
        $link     = get_permalink();
        $title    = get_the_title();

        // Región
        $regions = get_the_terms($post_id, 'region_europamundo');
        $region_name = ($regions && !is_wp_error($regions)) ? $regions[0]->name : '';

        // Imagen
        $img_html = '';
        if (has_post_thumbnail()) {
            $img_html = get_the_post_thumbnail($post_id, 'medium_large', array('loading' => 'lazy'));
        }

        // Badge de precio
        $badge = '';
        if ($precio) {
            $noches = $dias ? (intval($dias) - 1) . 'N' : '';
            $dias_label = $dias ? $dias . 'D' : '';
            $badge = '<div class="emc-badge">Desde<br>USD <strong>' . esc_html($precio) . '</strong> <small>' . esc_html($dias_label) . ' ' . esc_html($noches) . '</small></div>';
        }

        $html .= '
        <div class="emc-card">
            <div class="emc-card-img">
                ' . $img_html . '
                ' . $badge . '
                <a href="' . esc_url($wa_link) . '" target="_blank" rel="noopener" class="emc-wa-btn">' . $wa_svg . ' Contacta a una asesora</a>
            </div>
            <div class="emc-card-body">';

        if ($region_name) {
            $html .= '<div class="emc-card-region">' . esc_html($region_name) . '</div>';
        }

        $html .= '
                <div class="emc-card-title"><a href="' . esc_url($link) . '">' . esc_html($title) . '</a></div>';

        if ($fechas) {
            $html .= '<div class="emc-card-meta">' . esc_html($fechas) . '</div>';
        }

        $html .= '
                <div class="emc-card-services">
                    <span>🚌 Transporte</span>
                    <span>🏨 Alojamiento</span>
                    <span>🎯 Guiado</span>
                </div>
                <a href="' . esc_url($link) . '" class="emc-card-btn">Ver Detalles</a>
            </div>
        </div>';
    }

    $html .= '</div>';
    wp_reset_postdata();

    return $html;
}
add_shortcode('europamundo_circuitos', 'europamundo_circuitos_shortcode');

// ══════════════════════════════════════════════════════
// FLUSH REWRITE RULES AL ACTIVAR/DESACTIVAR
// ══════════════════════════════════════════════════════

function europamundo_activate() {
    europamundo_register_cpt();
    europamundo_register_region_taxonomy();
    europamundo_register_serie_taxonomy();
    europamundo_create_default_terms();
    europamundo_create_menu();
    flush_rewrite_rules();
}
register_activation_hook(__FILE__, 'europamundo_activate');

function europamundo_deactivate() {
    flush_rewrite_rules();
}
register_deactivation_hook(__FILE__, 'europamundo_deactivate');
