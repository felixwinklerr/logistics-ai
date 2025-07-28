/**
 * Romanian Localization Framework
 * Provides Romanian language support and cultural formatting
 */

export interface RomanianLocalization {
  // Workflow states
  workflowStates: Record<string, string>;
  
  // Common freight forwarding terms
  freight: Record<string, string>;
  
  // Form labels and validation messages
  forms: Record<string, string>;
  
  // Date and currency formatting
  formatting: {
    dateFormat: string;
    currencyFormat: string;
    numberFormat: string;
  };
}

export const romanianLocalization: RomanianLocalization = {
  workflowStates: {
    draft: 'Schiță',
    document_uploaded: 'Document Încărcat',
    ai_processing: 'Procesare AI',
    validation_required: 'Validare Necesară',
    validated: 'Validat',
    pricing_calculated: 'Preț Calculat',
    confirmed: 'Confirmat',
    subcontractor_assigned: 'Subcontractor Asignat',
    in_transit: 'În Tranzit',
    customs_clearance: 'Vămuire',
    delivered: 'Livrat',
    invoiced: 'Facturat',
    paid: 'Plătit',
    completed: 'Finalizat',
    cancelled: 'Anulat'
  },

  freight: {
    order: 'Comandă',
    shipment: 'Expediție',
    transport: 'Transport',
    freight: 'Marfă',
    cargo: 'Încărcătură',
    pickup: 'Ridicare',
    delivery: 'Livrare',
    weight: 'Greutate',
    volume: 'Volum',
    dimensions: 'Dimensiuni',
    route: 'Rută',
    distance: 'Distanță',
    subcontractor: 'Subcontractor',
    carrier: 'Transportator',
    driver: 'Șofer',
    vehicle: 'Vehicul',
    trailer: 'Remorcă',
    documentation: 'Documentație',
    invoice: 'Factură',
    payment: 'Plată',
    customs: 'Vama',
    border: 'Frontieră',
    clearance: 'Vămuire'
  },

  forms: {
    // Address fields
    street: 'Strada',
    number: 'Numărul',
    city: 'Orașul',
    county: 'Județul',
    postalCode: 'Cod Poștal',
    country: 'Țara',
    
    // Company fields
    companyName: 'Denumirea Companiei',
    vatNumber: 'Cod TVA',
    registrationNumber: 'Număr Înregistrare',
    
    // Contact fields
    contactPerson: 'Persoana de Contact',
    phone: 'Telefon',
    email: 'Email',
    
    // Shipment fields
    description: 'Descrierea Mărfii',
    weight: 'Greutate (kg)',
    volume: 'Volum (m³)',
    length: 'Lungime (cm)',
    width: 'Lățime (cm)',
    height: 'Înălțime (cm)',
    
    // Validation messages
    required: 'Câmp obligatoriu',
    invalidVat: 'Cod TVA invalid (format: RO + 2-10 cifre)',
    invalidPostalCode: 'Cod poștal invalid (6 cifre)',
    invalidCounty: 'Cod județ invalid',
    invalidEmail: 'Adresă email invalidă',
    invalidPhone: 'Număr de telefon invalid',
    
    // Actions
    save: 'Salvează',
    cancel: 'Anulează',
    edit: 'Editează',
    delete: 'Șterge',
    confirm: 'Confirmă',
    submit: 'Trimite',
    upload: 'Încarcă',
    download: 'Descarcă',
    print: 'Tipărește',
    
    // Status
    loading: 'Se încarcă...',
    saving: 'Se salvează...',
    success: 'Succes',
    error: 'Eroare',
    warning: 'Avertisment',
    info: 'Informație'
  },

  formatting: {
    dateFormat: 'DD.MM.YYYY',
    currencyFormat: '{amount} {currency}',
    numberFormat: '0,0.00'
  }
};

/**
 * Romanian VAT number validator
 */
export const validateRomanianVAT = (vatNumber: string): boolean => {
  if (!vatNumber) return false;
  
  // Remove spaces and convert to uppercase
  const cleanVat = vatNumber.replace(/\s/g, '').toUpperCase();
  
  // Check Romanian VAT pattern: RO + 2-10 digits
  const romanianVatPattern = /^RO\d{2,10}$/;
  return romanianVatPattern.test(cleanVat);
};

/**
 * Romanian postal code validator
 */
export const validateRomanianPostalCode = (postalCode: string): boolean => {
  if (!postalCode) return false;
  
  // Remove spaces and check for 6 digits
  const cleanCode = postalCode.replace(/\s/g, '');
  return cleanCode.length === 6 && /^\d{6}$/.test(cleanCode);
};

/**
 * Romanian county (județ) validator
 */
export const validateRomanianCounty = (county: string): boolean => {
  if (!county) return false;
  
  const validCounties = [
    'AB', 'AR', 'AG', 'BC', 'BH', 'BN', 'BT', 'BV', 'BR', 'BZ',
    'CS', 'CL', 'CJ', 'CT', 'CV', 'DB', 'DJ', 'GL', 'GR', 'GJ',
    'HR', 'HD', 'IL', 'IS', 'IF', 'MM', 'MH', 'MS', 'NT', 'OT',
    'PH', 'SM', 'SJ', 'SB', 'SV', 'TR', 'TM', 'TL', 'VS', 'VL',
    'VN', 'B'
  ];
  
  return validCounties.includes(county.toUpperCase());
};

/**
 * Format Romanian currency
 */
export const formatRomanianCurrency = (
  amount: number, 
  currency: 'RON' | 'EUR' = 'RON'
): string => {
  const formattedAmount = new Intl.NumberFormat('ro-RO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
  
  return `${formattedAmount} ${currency}`;
};

/**
 * Format Romanian date
 */
export const formatRomanianDate = (date: Date | string): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  return new Intl.DateTimeFormat('ro-RO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).format(dateObj);
};

/**
 * Format Romanian address
 */
export const formatRomanianAddress = (address: {
  street?: string;
  number?: string;
  city?: string;
  county?: string;
  postalCode?: string;
}): string => {
  const parts = [];
  
  if (address.street && address.number) {
    parts.push(`${address.street} ${address.number}`);
  } else if (address.street) {
    parts.push(address.street);
  }
  
  if (address.city) {
    parts.push(address.city);
  }
  
  if (address.county) {
    parts.push(`jud. ${address.county.toUpperCase()}`);
  }
  
  if (address.postalCode) {
    parts.push(address.postalCode);
  }
  
  parts.push('România');
  
  return parts.join(', ');
};

/**
 * Get localized text
 */
export const getLocalizedText = (key: string, section?: keyof RomanianLocalization): string => {
  if (section && romanianLocalization[section]) {
    const sectionData = romanianLocalization[section];
    if (typeof sectionData === 'object' && key in sectionData) {
      return (sectionData as Record<string, string>)[key];
    }
  }
  
  // Search in all sections
  for (const sectionKey of Object.keys(romanianLocalization)) {
    const sectionData = romanianLocalization[sectionKey as keyof RomanianLocalization];
    if (typeof sectionData === 'object' && key in sectionData) {
      return (sectionData as Record<string, string>)[key];
    }
  }
  
  // Return key if not found (fallback)
  return key;
};

/**
 * Romanian business hours helper
 */
export const isRomanianBusinessHours = (date: Date = new Date()): boolean => {
  const hour = date.getHours();
  const day = date.getDay(); // 0 = Sunday, 6 = Saturday
  
  // Monday to Friday, 9 AM to 6 PM
  return day >= 1 && day <= 5 && hour >= 9 && hour < 18;
};

/**
 * Romanian national holidays (simplified)
 */
export const isRomanianNationalHoliday = (date: Date): boolean => {
  const month = date.getMonth() + 1; // 0-indexed to 1-indexed
  const day = date.getDate();
  
  const holidays = [
    [1, 1],   // New Year's Day
    [1, 2],   // Day after New Year
    [1, 6],   // Epiphany
    [5, 1],   // Labour Day
    [8, 15],  // Assumption of Mary
    [11, 30], // Saint Andrew's Day
    [12, 1],  // National Day
    [12, 25], // Christmas Day
    [12, 26]  // Second day of Christmas
  ];
  
  return holidays.some(([hMonth, hDay]) => month === hMonth && day === hDay);
};

export default romanianLocalization;
