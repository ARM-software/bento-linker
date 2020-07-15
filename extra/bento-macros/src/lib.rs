extern crate proc_macro;
use proc_macro::TokenStream;
use proc_macro2::TokenStream as TokenStream2;
use proc_macro2::TokenTree as TokenTree2;
use proc_macro2::Span;
use syn::parse_macro_input;
use syn::parse_quote;
use syn::parse::Parse;
use syn::parse::ParseStream;
use syn::spanned::Spanned;
use quote::quote;
use std::sync::atomic;

static SEEN_EXPORTS: atomic::AtomicBool
    = atomic::AtomicBool::new(false);

#[derive(Clone)]
struct ExportExportAttrs {
    link_name: Option<syn::LitStr>,
    ty: syn::Type,
}

impl Parse for ExportExportAttrs {
    fn parse(input: ParseStream) -> syn::Result<Self> {
        let mut link_name = None;
        let mut ty = None;
        while !input.is_empty() {
            // parse attributes
            let attr = if input.peek(syn::Token![type]) {
                let token = input.parse::<syn::Token![type]>()?;
                syn::Ident::new("type", token.span())
            } else {
                input.parse::<syn::Ident>()?
            };

            match attr.to_string().as_ref() {
                "link_name" => {
                    input.parse::<syn::Token![=]>()?;
                    let s = input.parse::<syn::LitStr>()?;
                    link_name = Some(s);
                }
                "type" => {
                    input.parse::<syn::Token![=]>()?;
                    let f = input.parse::<syn::Type>()?;
                    ty = Some(f);
                }
                _ => {
                    Err(syn::Error::new(attr.span(),
                        format!("unknown export attribute `{}`", attr)))?;
                }
            };

            input.parse::<Option<syn::Token![,]>>()?;
        }

        // require type
        let ty = ty.ok_or_else(|| syn::Error::new(
            Span::call_site(), "export missing `type`"))?;

        Ok(ExportExportAttrs{link_name, ty})
    }
}

#[proc_macro_attribute]
pub fn export_export(attrs: TokenStream, input: TokenStream) -> TokenStream {
    // parse
    let attrs = parse_macro_input!(attrs as ExportExportAttrs);
    let f = parse_macro_input!(input as syn::ItemFn);

    let name = f.sig.ident.clone();
    let link_name = attrs.link_name.unwrap_or_else(||
        syn::LitStr::new(&name.to_string(), name.span()));
    let export_name = syn::Ident::new(
        &format!("__box_export_{}", name),
        name.span());
    let ty = attrs.ty;

    let export_f = syn::ItemFn{
        attrs: vec![
            parse_quote!{#[export_name=#link_name]}
        ],
        vis: syn::Visibility::Inherited,
        sig: syn::Signature{
            abi: parse_quote!{extern "C"},
            ..f.sig.clone()
        },
        ..f
    };

    let extern_f = syn::ForeignItemFn{
        attrs: f.attrs,
        vis: f.vis,
        sig: f.sig,
        semi_token: parse_quote!{;},
    };

    // convert to tokens so we can replace the reference with a
    // macro identifier
    fn replace_ident(
        tokens: TokenStream2,
        from: &syn::Ident,
        to: &TokenStream2
    ) -> TokenStream2 {
        let mut ntokens = vec![];
        for token in tokens {
            match token {
                TokenTree2::Ident(ident) if &ident == from => {
                    ntokens.extend(to.clone());
                }
                TokenTree2::Group(group) => {
                    ntokens.push(TokenTree2::Group(proc_macro2::Group::new(
                            group.delimiter(),
                            replace_ident(group.stream(), from, to))));
                }
                _ => {
                    ntokens.push(token);
                }
            }
        }
        ntokens.into_iter().collect()
    }

    let predeclarations = if !SEEN_EXPORTS.swap(
            true, atomic::Ordering::SeqCst) {
        Some(quote!{pub use crate as __box_exports;})
    } else {
        None
    };

    let ma = quote! {
        ($name:ident) => {
            const _: #ty = $name;
            #export_f
        };
    };
    let ma = replace_ident(
            ma, &export_name, &quote!{$name});
    let ma = replace_ident(
            ma, &syn::Ident::new("__box_exports", Span::call_site()),
                &quote!{$crate});
    let ma = replace_ident(
            ma, &name, &quote!{#export_name});

    let q = quote! {
        // need to re-declare because macros are placed in crate root
        #predeclarations

        // macro that generates the export
        #[macro_export]
        macro_rules! #export_name {
            #ma
        }

        // expose linkage here
        extern "C" {
            #[link_name=#link_name]
            #extern_f
        }
    };

    q.into()
}

#[proc_macro_attribute]
pub fn export(attrs: TokenStream, input: TokenStream) -> TokenStream {
    let path = parse_macro_input!(attrs as syn::Path);
    let f = parse_macro_input!(input as syn::ItemFn);

    let mut export_path = path.clone();
    let x = export_path.segments.pop().unwrap().into_value();
    export_path.segments.push(syn::PathSegment::from(syn::Ident::new(
        "__box_exports",
        x.span())));
    export_path.segments.push(syn::PathSegment::from(syn::Ident::new(
        &format!("__box_export_{}", x.ident),
        x.span())));

    let name = f.sig.ident.clone();
    let q = quote!{
        #export_path!(#name);
        #f
    };

    q.into()
}
